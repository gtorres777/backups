import json
import requests
import os
import sys
import csv
import subprocess
import getpass
import pathlib


"""
Usage: dump_odoo_db [url] [master_password] [directory to download]
"""


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

def get_list_db(url):
    action_url = 'http://{}/web/database/list'.format(url)
    data = {'params': {}}
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(action_url, data=json.dumps(data), headers=headers)
        db = response.json()
    except Exception as e:
        print('URL:', url)
        print('Connection establishment failed!')
        print(e)
        print('------------------------------')
        db = {'error': e}
    return db


def upload_dump_to_s3(list_db, data):
    url = data['url']
    master_password = data['master_password']
    directory = data['directory']
    for db in list_db:
        print('DATABASE:', db)
        if 'test' in db:
            print('Test database will not be downloaded!!!')
            continue
        else:
            dump_name = dump_db_odoo(db)
            if dump_name:
                bucket_name = 's3://backups-odoo-prod/{}/{}/{}'.format(url, db, dump_name)
                dir_dump = '{}{}'.format(directory, dump_name)
                operation = 'aws s3 cp {} {} --acl public-read --profile marco_ganemo'.format(dir_dump, bucket_name)
                print('Uploading...')
                os.system(operation)
                print('Bucket:', bucket_name)
                os.system('rm {}*'.format(directory))
        print('------------------')


def generate_backups():

    current_user = getpass.getuser()
    file_route = "/home/{0}/backup/".format(current_user)

    if not pathlib.Path(file_route).exists():
        os.system("mkdir /home/{0}/backup/".format(current_user))

    with open('host_data.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            data = {
                'url': row[0],
                'master_password': row[1],
                'directory': '/home/{0}/backup/'.format(current_user)
            }
            # url = sys.argv[1]
            # master_password = sys.argv[2] or 'admin'
            # directory = sys.argv[3]
            db = get_list_db(data['url'])
            if db.get('error'):
                print('¡CONNECTION PROBLEM!\n Review data and try again.')
            else:
                list_db = db['result']
                print('URL:', data['url'])
                upload_dump_to_s3(list_db, data)


def restore_backup(url, data):
    action_url = 'https://{}/web/database/restore'.format(url)
    try:
        print('Sending backup to {}'.format(url))
        requests.post(action_url, data=data)
        print('Backup was restored!')
        # db = response.json()
    except Exception as e:
        print('Connection establishment failed!')
        print(e)


def main():
    action = input('Action: ')
    if action.upper() == 'BACKUPS':
        generate_backups()
    elif action.upper() == 'RESTORE':
        # url = input('URL without protocal Http or Https: ')
        # master_password = input('Master password: ')
        # db_name = input('DB name: ')
        own_directory = '/home/odoo/Descargas/victorynk.zip'
        backup_file = open(own_directory, 'rb')
        url = 'victor.ganemo.co'
        master_password = 'A-GJPQJ6V8%nJQY6B4GzPCbBV'
        db_name = 'victorynk'
        dat = {
            'master_pwd': master_password,
            'backup_file': backup_file,
            'name': db_name
        }
        restore_backup(url, data)


if __name__ == "__main__":
    sys.exit(main())
