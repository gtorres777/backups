import json
import requests
import os
import sys
import csv
import subprocess
import getpass
import pathlib

import argparse
import time
from typing import NamedTuple
from datetime import timedelta



class Args(NamedTuple):
    """ Command-line arguments """
    url: str
    pod_name: str


def get_args() -> Args:

    """ Get command-line arguments """

    parser = argparse.ArgumentParser(
        description='Script for generating backups',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)


    parser.add_argument('url',
                        metavar='url',
                        help='url of the service')

    parser.add_argument('pod_name',
                        metavar='pod_name',
                        help='name of the pod')
                        
    args = parser.parse_args()


    return Args(args.url, args.pod_name)


def get_list_db(url):
    action_url = "http://{}/web/database/list".format(url)
    data = {"params": {}}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(action_url, data=json.dumps(data), headers=headers)
        db = response.json()
    except Exception as e:
        print("URL:", url)
        print("Connection establishment failed!")
        print(e)
        print("------------------------------")
        db = {"error": e}

    return db


def dump_db_odoo(db_name):

    try:
        operation = subprocess.check_output('sh odoo-backup.sh {}'.format(db_name),shell=True).decode('utf-8')
        print('Backup files generated')

        output_from_script = operation.splitlines()
        dump_name = output_from_script[-1]

    except Exception as e:
        dump_name = False
        print('Connection establishment failed!')
        print(e)

    return dump_name



def upload_dump_to_s3(list_db, data):
    pod_name = data['pod_name']
    directory = data['directory']
    for db in list_db:
        print('DATABASE:', db)
        if 'test' in db:
            print('Test database will not be downloaded!!!')
            continue
        else:
            dump_name = dump_db_odoo(db)
            if dump_name:
                bucket_name = 's3://backups-odoo-prod/{}/{}/{}'.format(pod_name, db, dump_name)
                dir_dump = '{}{}'.format(directory, dump_name)
                operation = 'aws s3 cp {} {} --acl public-read'.format(dir_dump, bucket_name)
                print('Uploading...')
                os.system(operation)
                print('Bucket:', bucket_name)
                os.system('rm {}*'.format(directory))
        print('------------------')



def generate_backups(url, pod_name):

    current_user = getpass.getuser()
    file_route = "/home/{0}/backup/".format(current_user)

    if not pathlib.Path(file_route).exists():
        os.system("mkdir /home/{0}/backup/".format(current_user))

    data = {
        'pod_name': pod_name,
        'directory': '/home/{0}/backup/'.format(current_user)
    }

    db = get_list_db(url)
    if db.get('error'):
        print('¡CONNECTION PROBLEM!\n Review data and try again.')
    else:
        list_db = db['result']
        print('POD:', data['pod_name'])
        upload_dump_to_s3(list_db, data)



def main():

    args = get_args()
    url, pod_name = args.url, args.pod_name

    generate_backups(url,pod_name)


if __name__ == '__main__':
    main()
