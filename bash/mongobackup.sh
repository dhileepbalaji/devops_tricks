#!/bin/bash

## BACKUP LOGIC
# 1. It will initialize environment variables regarding the mongo and backup files.
# 2. Dump the mongodb data in the /tmp/ folder and its name will be BACKUP_FILE_PATH.
# 3. Compress the data in tar.gz format that is present in /tmp/ folder.
# 4. Encrypt the compressed file using openssl using the ENCRYPTION_PASSPHRASE.
# 5. Remove the compressed and data dump directories.
# 6. Move the encrypted file to the BACKUP_DIR folder, this directory will contains all the encrypted backup files. Files older than 7 days will be removed.
# 7. rsync the BACKUP_DIR with the remote backup server



# ENVIRONMENT VARIABLES
BACKUP_DIR="/mnt/mongodb"
mkdir -p $BACKUP_DIR
# mongo vars
USER=admin
PASSWORD='testing'
HOSTS=127.0.0.1:27017

# backup vars
BACKUP_STATUS="/var/log/mongo-backup.stat"
touch $BACKUP_STATUS
# valid status codes are:
# 1: It means inprogress
# 2: It means success
# 3: It means error
COMMAND_STATUS_FILE="command.stat"
rm -rf $COMMAND_STATUS_FILE
touch $COMMAND_STATUS_FILE

DATE_TIME=$(date +"%d-%m-%Y-%s")
BACKUP_FILE=mongo-$DATE_TIME
BACKUP_FILE_PATH="/tmp/"mongo-$DATE_TIME
COMPRESSED_FILE=$BACKUP_FILE_PATH.tar.gz
ENCRYPTED_FILE=$COMPRESSED_FILE.enc
ENCRYPTION_PASSPHRASE=ew1quohDie0goh

mongo_dump_check () {
    # It will check the status of mongodump utility, if command executes sucessfully it will have an exitcode of 0 while in
    # other cases it will have exitcode other than zero. So this methods check if the exitcode is 0 it will echo a value in
    # /dev/null because we don't want that that values otherwise it will echo a value in the COMMAND_STATUS_FILE. This file
    # is used by check_error_status method to decide to whether continue the backup process or terminate the execution. In
    # case of termination it will enter a value in BACKUP_STATUS file. This file will be read by telegraf to insert the backup
    # process status in the influx db.
    #
    # The reason to use exitcode $? is becuase mongodump utility will always dump the debug data in stderr.

    [ $? == 0 ] && echo "${DATE_TIME} 2" >> /dev/null || echo "${DATE_TIME} 3" >> $COMMAND_STATUS_FILE;
}

check_error_status () {
    # It will check whether the COMMAND_STATUS_FILE is emtpy or not. In case its emtpy it means that command executed previously
    # didn't had any problem. If it has a value in it, it will enter a value in the BACKUP_STATUS file and terminate the code
    # execution.

    [ -s $COMMAND_STATUS_FILE ] && echo "${DATE_TIME} 3" >> $BACKUP_STATUS;
    [ -s $COMMAND_STATUS_FILE ] && exit 1;
}

# COMMAND DETAILS
# nice: it is a utility to assing priority to processes
# mongodump: it a utility to backup mongdb data
# openssl: it is used for data encryption and descryption
# rsync: utility for tranferring and syncing files between systems

# ARG DETAILS
# oplog: use oplog for taking a point-in-time snapshot, if used it copies all the data from the source database
#        as well as all of the oplog entries from the beginning to the end of the backup procedure.
#
#        NOTE:  In order to have an oplog you have to be running a replica set otherwise on single node it will fail.
# out: directory path in which files will be store
echo "${DATE_TIME} 1" >> $BACKUP_STATUS
# dumping the data
# NOTE: Not forwarding the mongodump command strerr output in a file because it output debug logs in stderr.
#       It is a bug therefore using exitcode
# NOTE 2: Here cannot backup a specific database beacuase according to docmumentation --db and --uri cannot be use together.
nice -n 10 /usr/bin/mongodump --uri mongodb://${USER}:${PASSWORD}@${HOSTS} --oplog --out=$BACKUP_FILE_PATH
mongo_dump_check
check_error_status

# compressing the backup data
nice -n 10 tar -czvf $COMPRESSED_FILE --directory="/tmp" $BACKUP_FILE 2> $COMMAND_STATUS_FILE
check_error_status

# encrypting data

# ARGS DETAILS
# md: Use specified digest to create a key from the passphrase
# pbkdf2: Use password-based key derivation function 2
# iter: iteration count and force use of PBKDF2
# salt: Use salt in the KDF
# in: input file name
# out: encrypted output file
# k: passphrase value
openssl enc -aes-256-cbc -md sha512 -pbkdf2 -iter 100000 -salt -in $COMPRESSED_FILE -out $ENCRYPTED_FILE -k $ENCRYPTION_PASSPHRASE 2> $COMMAND_STATUS_FILE
check_error_status

# removing files and directories
rm -r $BACKUP_FILE_PATH 2> $COMMAND_STATUS_FILE
check_error_status

rm $COMPRESSED_FILE 2> $COMMAND_STATUS_FILE
check_error_status

# rsync the "/mnt/backup" directory from live server to production backup servers "/home/production/backup/mongodb/" directory
mv $ENCRYPTED_FILE $BACKUP_DIR 2> $COMMAND_STATUS_FILE
check_error_status


# It will remove the files that are 7 days old
# ARGS DETAILS
# -mtime File's data was last modified n*24 hours ago.  See the comments for -atime to understand how rounding affects the interpretation of file modification times.
find $BACKUP_DIR  -mtime +10 -delete 2> $COMMAND_STATUS_FILE
check_error_status

# Add script to store the data in S3
COPY_DIR=$BACKUP_DIR
DAYS_TO_HOLD="7"
NOW=`date +%Y%m%d`
S3='gccagentx.backup.prod'
echo "Starting log cleanup process ..."

find ${COPY_DIR} -iname "*.enc" -mtime +${DAYS_TO_HOLD} -exec aws s3 cp {} s3://${S3}/backups/mongodump/ \;  >/dev/null 2>&1

echo "Log clean up completed"


[ -s $COMMAND_STATUS_FILE ] && echo "${DATE_TIME} 3" >> $BACKUP_STATUS || echo "${DATE_TIME} 2" >> $BACKUP_STATUS
exit 0

# CRON TIME
# * 0 * * * /scripts/mongobackup.sh 2>/tmp/mongodump.cron_err
