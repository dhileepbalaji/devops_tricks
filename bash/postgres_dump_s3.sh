#!/bin/bash

################# User Settings ################################
# Postgres credentials
PG_HOST=""
PG_USER=""
PG_PORT=5432
export PGPASSWORD=''
# List of databases to backup (comma separated)
PG_DATABASES=""

# Bucket and path within S3
S3BUCKET=''
S3PATH=""

#Mailing
TO=''

#Current Time
CTIME=`date +%Y%m%d_%H%M%S_%Z`
#################################################################
# Main Script *****Don't edit Below*****
#################################################################
set -Euf -o pipefail

# get script dir function
get_script_dir () {
     SOURCE="${BASH_SOURCE[0]}"
     # While $SOURCE is a symlink, resolve it
     while [ -h "$SOURCE" ]; do
          DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
          SOURCE="$( readlink "$SOURCE" )"
          # If $SOURCE was a relative symlink (so no "/" as prefix, need to resolve it relative to the symlink base directory
          [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
     done
     DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
     echo "$DIR"
}

#Logging Function
#Usage: log "This is test"
#LogFile
FILE_DATE=`date +%Y%m%d_%H%M%S_%Z`
LF_DIR=$(get_script_dir)
LF_DIR_LOGS="${LF_DIR}/logs"
mkdir -p ${LF_DIR_LOGS} || true
LF=${LF_DIR_LOGS}/pgdump-logs-${FILE_DATE}.log
touch $LF
chmod 664 $LF

function log {
	m_time=`date "+%F %T"`
	echo $m_time" "$* >> $LF
}

#commandstatuscheck function
function commandstatuscheck {
	if $1 >>$LF 2>&1 ; then
		log $2
	else 
		log $3
		MAILERRORMESSAGE="Pg_Dump Script Failed ! Attached the Log File ! Check ASAP!"
		SUBJECT="Pg_Dump Script Failed !"
		echo "$MAILERRORMESSAGE" | mutt -s "$SUBJECT" -a "$LF" -e  "my_hdr From:Devops <gccsecretagentx@gmail.com>" -- $TO
		exit 1
	fi
				
}

#Errors in script
function script_error {
	MAILERRORMESSAGE="Pg_Dump Script Failed ! Attached the Log File ! Check ASAP!"
	SUBJECT="Pg_Dump Script Failed !"
	echo "$MAILERRORMESSAGE" | mutt -s "$SUBJECT" -a "$LF" -e "my_hdr From:Devops <gccsecretagentx@gmail.com>" -- $TO

}


#Postgres Connection Check Function
function pg_connection_check {
	log "Executing pg_connection_check() function" 
	COMMAND="/usr/bin/pg_isready -h $1 -p $2"
	SUCESSMESSAGE="pg_connection_check(): Postgres connection Success!"
	FAILUREMESSAGE="pg_connection_check(): Error => Postgres connection Failed!"
	commandstatuscheck "${COMMAND}" "${SUCESSMESSAGE}" "${FAILUREMESSAGE}"
}

function s3upload {
	#Upload to S3BUCKET
	COMMAND="aws s3api put-object --bucket $1 --key $2\
	--body $3 --metadata md5chksum=$4 --content-md5 $4"
	SUCESSMESSAGE="s3upload () : Completed S3 Upload Process. Location: $1/$2"
	FAILUREMESSAGE="s3upload () : Error S3 Upload Process Failed!"
	commandstatuscheck "${COMMAND}" "${SUCESSMESSAGE}" "${FAILUREMESSAGE}"
    
	#MD5CHECK
	S3MD5=`aws s3api head-object --bucket $1 --key $2 | jq -r ."Metadata"."md5chksum"`
	COMMAND="[ $4 == ${S3MD5} ]"
	SUCESSMESSAGE="s3upload () : Uploaded File Integrity check passed! MD5 Matched : ${S3MD5}"
	FAILUREMESSAGE="s3upload (): Uploaded File Integrity check Failed! MD5 Not Matched"
	commandstatuscheck "${COMMAND}" "${SUCESSMESSAGE}" "${FAILUREMESSAGE}"
}

# pg_dump function
function pg_dump_db {
	log "Executing pg_dump_db() function" 
	log "pg_dump_db() : Checking Postgress connection to $PG_HOST"
	pg_connection_check $PG_HOST $PG_PORT
    DB=$1
    BACKUPFOLDER=$(get_script_dir)
	BACKUPFILE=${BACKUPFOLDER}/${PG_HOST}_${DB}_${CTIME}.dump
	if [ ! -f ${BACKUPFILE} ]; then
		log "pg_dump_db() : Postgress dump Started for the ${DB} "
		if /usr/bin/pg_dump -Fc -h $PG_HOST -U $PG_USER -p $PG_PORT $DB > ${BACKUPFILE} 2>>$LF &&\
			tar -zvcf "${BACKUPFILE}.tar.gz" ${BACKUPFILE} 2>>$LF ; then
			log "pg_dump_db() : Postgres dump Completed for the ${DB} "
			else
			log "pg_dump_db() : Postgres dump failed for the ${DB}"
			rm -rf $BACKUPFILE
			script_error
			exit 1
		fi
	fi
	GZIPMD5VALUE=`openssl md5 -binary "${BACKUPFILE}.tar.gz" | base64`

}

# Split databases
IFS=',' read -ra DBS <<< "$PG_DATABASES"

log "INFO => Postgres Backup Script Started "

# Loop thru databases
for db in "${DBS[@]}"; do
    log "INFO => Backup Started for $db "

    # Dump database
    log "INFO => Dump Database in Progress for $db "
    pg_dump_db $db

    # Copy to S3
    log "INFO => Copying files to s3 Bucket "
    s3upload "${S3BUCKET}" "${S3PATH}/${PG_HOST}_${DB}_${CTIME}.tar.gz" "${BACKUPFILE}.tar.gz" "${GZIPMD5VALUE}"

    log "INFO => Removing local file "
    rm -rf "${BACKUPFILE}.tar.gz" ${BACKUPFILE} || true

    # Log
    log "INFO => Backup completed for $db"
done

log "Success => Postrgres Backup completed"
