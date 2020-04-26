#!/usr/bin/python
import argparse
import multiprocessing
import boto3
import os
import Queue
from datetime import datetime


class Downloader(object):
    def __init__(self, bucket_name,file_list, num_processes=8):
        self.bucket_name = bucket_name
        self.num_processes = num_processes
        self.file_list = file_list
        self.task_queue = multiprocessing.JoinableQueue()
        self.s3 = boto3.resource('s3')
        self.n_tasks = 0
        self.shared_list = multiprocessing.Manager()
        self.shared_list = self.shared_list.list()


    def queue_tasks(self):
        for key in self.file_list:
            self.task_queue.put(key)
            self.n_tasks += 1

    def worker(self, input):
        while 1:
            try:
                key_name = input.get(True, 1)
            except Queue.Empty:
                p_name =  multiprocessing.current_process().name
                break
            try:
                self.s3.Bucket(self.bucket_name).download_file(key_name, key_name)
                self.shared_list.append(key_name)
                input.task_done()
            except Exception as e:
                print 'Error processing %s' %key_name
                input.task_done()

    def main(self):
        self.queue_tasks()
        for i in range(self.num_processes):
            multiprocessing.Process(target=self.worker,
                                    args=(self.task_queue,)).start()
        self.task_queue.join()
        self.task_queue.close()
        print 'Requested files => {}'.format(self.n_tasks)
        print 'Completed files => {}'.format(len(self.shared_list))



# Argument parser
parser = argparse.ArgumentParser(description='Download files from s3 Bucket')
parser.add_argument('s3bucket', metavar='Bucket', type=str, nargs=1,
                    help='Enter the Bucket Name')
parser.add_argument('s3files', metavar='s3files', type=str, nargs=1,
                    help='Enter the filename containing the list of files to download')
args = parser.parse_args()

# Create List from Input
s3file_list = open(args.s3files[0]).read().split()
s3 = boto3.resource('s3')
Bucket = args.s3bucket[0]
# output dir
now = datetime.now()
path = str(Bucket) + str(now.strftime("%d%m%y_%H_%M"))
os.mkdir(path)
os.chdir(path)
#Download files
download = Downloader(Bucket,s3file_list)
download.main()
