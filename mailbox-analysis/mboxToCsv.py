!#/usr/bin/python
import base64
import csv
import mailbox
import os
import time
from argparse import ArgumentParser
from tqdm import tqdm
from bs4 import BeautifulSoup


def main(mbox_file, output_dir,SUBJECT):
    print("Reading mbox file")
    mbox = mailbox.mbox(mbox_file, factory=custom_reader)
    print("{} messages to parse".format(len(mbox)))
    parsed_data = []
    attachments_dir = os.path.join(output_dir, "attachments")

    if not os.path.exists(attachments_dir):
        os.makedirs(attachments_dir)
    columns = [
        "Date", "From", "To", "Subject", "Return-Path",
        "Content-Type", "Message-ID", "num_attachments_exported", "export_path"]

    for message in tqdm(mbox):
        msg_data = dict()
        header_data = dict(message._headers)
        try:
            if not header_data['Subject'].strip() == SUBJECT:
                body = getBody(message)
                body = body[:32000]
                for hdr in columns:
                    msg_data[hdr] = header_data.get(hdr, "N/A")
                if len(message.get_payload()):
                    export_path = write_payload(message, attachments_dir)
                    msg_data['num_attachments_exported'] = len(export_path)
                    msg_data['export_path'] = ", ".join(export_path)
                    msg_data['body'] = body
                    parsed_data.append(msg_data)
                    create_report(parsed_data, os.path.join(output_dir, "mbox_report.csv"), columns)
        except Exception as e:
            print(e)



def write_payload(msg, out_dir):
    pyld = msg.get_payload()
    export_path = []
    if msg.is_multipart():
        for entry in pyld:
            export_path += write_payload(entry, out_dir)
    else:
        content_type = msg.get_content_type()
        try:
            if "application/" in content_type.lower():
                content = base64.b64decode(msg.get_payload())
                export_path.append(export_content(msg, out_dir, content))
            elif "image/" in content_type.lower():
                content = base64.b64decode(msg.get_payload())
                export_path.append(export_content(msg, out_dir, content))
            elif "video/" in content_type.lower():
                content = base64.b64decode(msg.get_payload())
                export_path.append(export_content(msg, out_dir, content))
            elif "audio/" in content_type.lower():
                content = base64.b64decode(msg.get_payload())
                export_path.append(export_content(msg, out_dir, content))
            elif "text/csv" in content_type.lower():
                content = base64.b64decode(msg.get_payload())
                export_path.append(export_content(msg, out_dir, content))
            elif "info/" in content_type.lower():
                export_path.append(export_content(msg, out_dir,
                                              msg.get_payload()))
            elif "text/calendar" in content_type.lower():
                export_path.append(export_content(msg, out_dir,
                                              msg.get_payload()))
            elif "text/rtf" in content_type.lower():
                export_path.append(export_content(msg, out_dir,
                                              msg.get_payload()))
            else:
                if "name=" in msg.get('Content-Disposition', "NA"):
                    content = base64.b64decode(msg.get_payload())
                    export_path.append(export_content(msg, out_dir, content))
                elif "name=" in msg.get('Content-Type', "N/A"):
                    content = base64.b64decode(msg.get_payload())
                    export_path.append(export_content(msg, out_dir, content))
        except Exception as e:
            print("e")

    return export_path


def create_report(output_data, output_file, columns):
    with open(output_file, 'w', newline="",encoding='utf-8') as outfile:
        columns.append("body")
        csvfile = csv.DictWriter(outfile, columns)
        csvfile.writeheader()
        csvfile.writerows(output_data)
        columns.remove("body")


def custom_reader(data_stream):
    data = data_stream.read()
    try:
        content = data.decode("ascii")
    except (UnicodeDecodeError, UnicodeEncodeError) as e:
        try:
            content = data.decode("utf-8", errors="replace")
        except Exception as e:
            content = data.decode("cp1252", errors="replace")
    return mailbox.mboxMessage(content)


def export_content(msg, out_dir, content_data):
    file_name = get_filename(msg)
    file_ext = "FILE"

    if "." in file_name: file_ext = file_name.rsplit(".", 1)[-1]
    file_name = "{}_{:.4f}.{}".format(file_name.rsplit(".", 1)[0], time.time(), file_ext)
    file_name = os.path.join(out_dir, file_name)
    if isinstance(content_data, str):
        open(file_name, 'w').write(content_data)
    else:
        open(file_name, 'wb').write(content_data)
    return file_name

def getcharsets(msg):
    charsets = set({})
    for c in msg.get_charsets():
        if c is not None:
            charsets.update([c])
    return charsets

def getBody(msg):
    while msg.is_multipart():
        msg=msg.get_payload()[0]
    t=msg.get_payload(decode=True)
    for charset in getcharsets(msg):
        try:
            t=t.decode(charset)
        except Exception as e:
            print("here")
    return BeautifulSoup(t,"html.parser").text


def get_filename(msg):

    if 'name=' in msg.get("Content-Disposition", "N/A"):
        fname_data = msg["Content-Disposition"].replace("\r\n", " ")
        fname = [x for x in fname_data.split("; ") if 'name=' in x]
        file_name = fname[0].split("=", 1)[-1]
    elif 'name=' in msg.get("Content-Type", "N/A"):
        fname_data = msg["Content-Type"].replace("\r\n", " ")
        fname = [x for x in fname_data.split("; ") if 'name=' in x]
        file_name = fname[0].split("=", 1)[-1]
    else:
        file_name = "NO_FILENAME"
    fchars = [x for x in file_name if x.isalnum() or x.isspace() or x == "."]
    return "".join(fchars)


if __name__ == '__main__':
    parser = ArgumentParser('Parsing MBOX files')
    parser.add_argument("MBOX", help="Path to mbox file")
    parser.add_argument(
        "OUTPUT_DIR", help="Path to output directory to write report ""and exported content")
    args = parser.parse_args()
    SUBJECT = "FW: FEB Rate reduction Loan documents for Review"
    main(args.MBOX, args.OUTPUT_DIR,SUBJECT)
