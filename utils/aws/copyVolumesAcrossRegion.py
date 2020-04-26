import logging
import sys
import threading

import boto3
import botocore

# LOGGING
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('instance_replication.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - (%(threadName)-10s) - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logging.getLogger('botocore').setLevel(logging.CRITICAL)

def copyvolume(source_conn, source_client, dest_conn, dest_client, source_region, src_instance,
               volume, dest_region, dest_instance, dest_device_mappings, ):
    # Source Waiter
    waiter_snapshot_complete = source_client.get_waiter('snapshot_completed')
    # Dest Waiter
    dest_waiter_snapshot_complete = dest_client.get_waiter('snapshot_completed')
    waiter_volume_available = dest_client.get_waiter('volume_available')
    waiter_volume_in_use = dest_client.get_waiter('volume_in_use')

    logger.info('Started creating Snapshot for {} in {}'.format(volume, source_region))
    src_devicename = volume.attachments[0]['Device']
    dest_current_volume_data = {}
    src_snapshot = source_conn.create_snapshot(
        VolumeId=volume.id,
        Description='Snapshot of volume ({})'.format(volume.id),
    )

    waiter_snapshot_complete.config.max_attempts = 240

    try:
        waiter_snapshot_complete.wait(
            SnapshotIds=[
                src_snapshot.id,
            ]
        )
    except botocore.exceptions.WaiterError as e:
        src_snapshot.delete()
        sys.exit('ERROR: {}'.format(e))
    logger.info('Snapshot completed for {}. Snapshot ID:{}'.format(volume, src_snapshot.id))
    logger.info('Started Copying Snapshot:{} from {} to {}'.format(src_snapshot.id, source_region, dest_region))
    dest_snapshot_id = dest_client.copy_snapshot(
        Description='Snapshot Copied from {}:- Instance_ID:{}, Volume_ID: {}, Mount_Point:{}'
            .format(source_region, src_instance.id, volume.id, src_devicename),
        DestinationRegion=dest_region,
        SourceRegion=source_region,
        SourceSnapshotId=str(src_snapshot.id),
    )
    dest_waiter_snapshot_complete.config.max_attempts = 240
    try:
        dest_waiter_snapshot_complete.wait(
            SnapshotIds=[
                dest_snapshot_id['SnapshotId'],
            ]
        )
    except botocore.exceptions.WaiterError as e:
        src_snapshot.delete()
        sys.exit('ERROR: {}'.format(e))
    logger.info('Copy Snapshot completed from {} to {}. Copied Snapshot ID:{}'
                 .format(source_region, dest_region, dest_snapshot_id['SnapshotId']))
    logger.info('Creating volume from copied snapshot:{} in {}'.format(dest_snapshot_id['SnapshotId'], dest_region))

    if volume.volume_type == 'io1':
        dest_volume = dest_conn.create_volume(
            SnapshotId=dest_snapshot_id['SnapshotId'],
            VolumeType=volume.volume_type,
            Iops=volume.iops,
            AvailabilityZone=dest_instance.placement['AvailabilityZone']
        )
    else:
        dest_volume = dest_conn.create_volume(
            SnapshotId=dest_snapshot_id['SnapshotId'],
            VolumeType=volume.volume_type,
            AvailabilityZone=dest_instance.placement['AvailabilityZone']
        )
    try:
        waiter_volume_available.wait(
            VolumeIds=[
                dest_volume.id,
            ],
        )
    except botocore.exceptions.WaiterError as e:
        src_snapshot.delete()
        dest_client.delete_snapshot(SnapshotId=dest_snapshot_id['SnapshotId'])
        dest_volume.id.delete()
        sys.exit('ERROR: {}'.format(e))

    logger.info('Volume created successfully in {} Volume ID:{}'
                 .format(dest_region, dest_volume.id))
    logger.info('Getting the destination instance device attachment details')
    for mapping in dest_device_mappings:
        if mapping['DeviceName'] == volume.attachments[0]['Device']:
            dest_current_volume_data = {
                'volume': mapping['VolumeId'],
                'DeleteOnTermination': mapping['DeleteOnTermination'],
                'DeviceName': mapping['DeviceName'],
            }
    if dest_current_volume_data:
        logger.info('Detaching the existing volume:{} from destination instance:{}. Mount point:{}'
                        .format(dest_current_volume_data['volume'], dest_instance,
                                dest_current_volume_data['DeviceName']))
        dest_instance.detach_volume(
                VolumeId=dest_current_volume_data['volume'],
                Device=dest_current_volume_data['DeviceName']
            )
        try:
                waiter_volume_available.wait(
                    VolumeIds=[
                        dest_current_volume_data['volume'],
                    ],
                )
        except botocore.exceptions.WaiterError as e:
                src_snapshot.delete()
                dest_client.delete_snapshot(SnapshotId=dest_snapshot_id['SnapshotId'])
                dest_volume.id.delete()
                sys.exit('ERROR: {}'.format(e))
        logger.info('Successfully Detached the existing volume:{} from destination instance:{}'
                         .format(dest_current_volume_data['volume'], dest_instance))
        logger.info('Attaching the newly created volume:{} to destination instance:{}. Mount point:{}'
                        .format(dest_volume.id, dest_instance,
                                dest_current_volume_data['DeviceName']))
        dest_instance.attach_volume(
                VolumeId=dest_volume.id,
                Device=dest_current_volume_data['DeviceName']
            )
        try:
                waiter_volume_in_use.wait(
                    VolumeIds=[
                        dest_volume.id,
                    ],
                )
        except botocore.exceptions.WaiterError as e:
                logger.debug(
                'Failed to attach the Newly Created Volume. Attaching the Old Volume:{} to destination instance.'
                'Mount Point:{}'
                .format(dest_current_volume_data['volume'], volume.attachments[0]['Device'])
                )
                dest_instance.attach_volume(
                VolumeId=dest_current_volume_data['volume'],
                Device=volume.attachments[0]['Device']
                )
                src_snapshot.delete()
                dest_client.delete_snapshot(SnapshotId=dest_snapshot_id['SnapshotId'])
                dest_volume.id.delete()
                sys.exit('ERROR: {}'.format(e))
        logger.info('Successfully Attached the New volume:{} to destination instance:{}'
                         .format(dest_volume.id, dest_instance))
    else:
        logger.info(
                'Mountpoint not found,New volume found in Source instance. Attaching it to destination instance')
        logger.info('Attaching the New volume:{} to destination instance:{}. Mount point:{}'
                        .format(dest_volume.id, dest_instance,
                                volume.attachments[0]['Device']))
        dest_instance.attach_volume(
                VolumeId=dest_volume.id,
                Device=volume.attachments[0]['Device']
            )
        try:
            waiter_volume_in_use.wait(
                    VolumeIds=[
                        dest_volume.id,
                    ],
                )
        except botocore.exceptions.WaiterError as e:
            logger.debug('Failed to attach the Newly Created Volume. Attaching the Old Volume:{} to destination instance.'
                         'Mount Point:{}'
                         .format(dest_current_volume_data['volume'],volume.attachments[0]['Device'])
                        )
            dest_instance.attach_volume(
                VolumeId=dest_current_volume_data['volume'],
                Device=volume.attachments[0]['Device']
            )
            src_snapshot.delete()
            dest_client.delete_snapshot(SnapshotId=dest_snapshot_id['SnapshotId'])
            dest_volume.id.delete()
            sys.exit('ERROR: {}'.format(e))
        logger.info('Successfully Attached the New volume:{} to destination instance:{}'
                         .format(dest_volume.id, dest_instance))
            # Delete Source and Destaination Snapshots.
    logger.info('Deleting the Source Snapshot:{},Destination Snapshot:{}'.format(src_snapshot.id, dest_snapshot_id))
    src_snapshot.delete()  # Source Snapshot
    dest_client.delete_snapshot(SnapshotId=dest_snapshot_id['SnapshotId'])  # Destination Snapshot
    try:
        dest_client.delete_volume(VolumeId=dest_current_volume_data['volume'])
        logger.info(
                'Deleted the Destination Volume:{}'.format(dest_current_volume_data['volume']))
    except KeyError:
        logger.info('Destination volume not found, Maybe its a newly created volume from Source instance')
        pass


def InstanceVolumeReplicate(source_region, src_instance, dest_region, dest_instance):
    # Session Initialization
    session = boto3.session.Session()
    source_client = session.client('ec2', region_name=source_region)
    source_ec2_conn = session.resource('ec2', region_name=source_region)
    dest_client = session.client('ec2', region_name=dest_region)
    dest_ec2_conn = session.resource('ec2', region_name=dest_region)
    # VARIABLES AND CONNECTION
    src_instance = source_ec2_conn.Instance(src_instance)
    dest_instance = dest_ec2_conn.Instance(dest_instance)
    # STORING THE ATTACHED DEVICES IN DESTINATION INSTANCE TO LIST
    dest_device_mappings = []
    dest_block_device_mappings = dest_instance.block_device_mappings
    # ITERATING AND STORING THE ATTACHED DEVICES PROPERTIES OF DESTINATION INSTANCE
    for device_mapping in dest_block_device_mappings:
        original_mappings = {
            'DeleteOnTermination': device_mapping['Ebs']['DeleteOnTermination'],
            'VolumeId': device_mapping['Ebs']['VolumeId'],
            'DeviceName': device_mapping['DeviceName'],
        }
        dest_device_mappings.append(original_mappings)

    # ITERATING AND REPLICATING THE SOURCE INSTANCE VOLUMES TO DESTINATION INSTANCE
    source_volumes = [v for v in src_instance.volumes.all()]
    # THREADING FOR PARALLEL VOLUMES REPLICATION
    logger.info('Volume replication started from Source:{} to Destination:{}'.format(src_instance, dest_instance))
    list_threads = []
    for volume in source_volumes:
        t = threading.Thread(target=copyvolume,
                         args=(source_ec2_conn, source_client, dest_ec2_conn, dest_client, source_region, src_instance,
                               volume, dest_region, dest_instance, dest_device_mappings))
        list_threads.append(t)
        t.start()
    [t.join() for t in list_threads]
    logger.info('Volume replication Completed from Source:{} to Destination:{}'.format(src_instance, dest_instance))
        #############################################
