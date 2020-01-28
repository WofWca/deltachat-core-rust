#!/usr/bin/env python3
# if the yaml import fails, run "pip install pyyaml"

import sys
import os
import yaml

out_all = ""
out_domains = ""
count = 1


def cleanstr(s):
    s = s.strip()
    s = s.replace("\n", " ")
    s = s.replace("\\", "\\\\")
    s = s.replace("\"", "\\\"")
    return s


def file2url(f):
    f = f[f.rindex("/")+1:]
    f = f.replace(".md", "")
    f = f.replace(".", "-")
    return "https://providers.delta.chat/" + f


def process_data(data, file):
    global out_all, out_domains, count
    status = data.get("status", "")
    out_provider = "    static ref P" + str(count) + ": Provider = Provider {\n"
    if status == "OK" or status == "PREPARATION" or status == "BROKEN":
        out_provider += "        status: Status::" + status + ",\n"
    else:
        raise TypeError("bad status")

    comment = ""
    if not "domains" in data:
        raise TypeError("no domains found")
    for domain in data["domains"]:
        domain = cleanstr(domain)
        if domain == "" or domain.count(".") < 1:
            raise TypeError("bad domain: " + domain)
        out_domains += "        (\"" + domain + "\", &*P" + str(count) + "),\n"
        comment += domain + ", "

    out_server = ""
    has_imap = False
    has_smtp = False
    if "server" in data:
        for s in data["server"]:
            hostname = cleanstr(s.get("hostname", ""))
            port = int(s.get("port", ""))
            if hostname == "" or hostname.count(".") < 1 or port <= 0:
                raise TypeError("bad hostname or port")

            protocol = s.get("type", "").upper()
            if protocol == "IMAP":
                has_imap = True
            elif protocol == "SMTP":
                has_smtp = True
            else:
                raise TypeError("bad protocol")

            socket = s.get("socket", "").upper()
            if socket != "STARTTLS" and socket != "SSL":
                raise TypeError("bad socket")

            username_pattern = s.get("username_pattern", "EMAIL").upper()
            if username_pattern != "EMAIL" and username_pattern != "EMAILLOCALPART":
                raise TypeError("bad username pattern")

            out_server += ("            Server { protocol: " + protocol + ", socket: " + socket + ", hostname: \""
            + hostname + "\", port: " + str(port) + ", username_pattern: " + username_pattern + " },\n")

    if (not has_imap and not has_smtp) or (has_imap and has_smtp):
        out_provider += "        before_login_hint: \"" + cleanstr(data.get("before_login_hint", "")) + "\",\n"
        out_provider += "        after_login_hint: \"" + cleanstr(data.get("after_login_hint", "")) + "\",\n"
        out_provider += "        overview_page: \"" + file2url(file) + "\",\n"
        out_provider += "        server: vec![\n" + out_server + "        ],\n"
        out_provider += "    };\n\n"
    else:
        raise TypeError("SMTP and IMAP must be specified together or left out both")

    out_all += "    // " + file[file.rindex("/")+1:] + ": " + comment.strip(", ") + "\n" + out_provider


def process_file(file):
    global count
    print("processing file: " + file, file=sys.stderr)
    with open(file) as f:
        # load_all() loads "---"-separated yamls -
        # by coincidence, this is also the frontmatter separator :)
        data = next(yaml.load_all(f, Loader=yaml.SafeLoader))
        process_data(data, file)
        count += 1


def process_dir(dir):
    print("processing directory: " + dir, file=sys.stderr)
    files = [f for f in os.listdir(dir) if f.endswith(".md")]
    files.sort()
    for f in files:
        process_file(os.path.join(dir, f))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: update.py DIR_WITH_MD_FILES > data.rs")

    out_all = ("// file generated by src/provider/update.py\n\n"
    "use crate::provider::Protocol::*;\n"
    "use crate::provider::Socket::*;\n"
    "use crate::provider::UsernamePattern::*;\n"
    "use crate::provider::*;\n"
    "use std::collections::HashMap;\n\n"
    "lazy_static::lazy_static! {\n\n")

    process_dir(sys.argv[1])

    out_all += "    pub static ref PROVIDER_DATA: HashMap<&'static str, &'static Provider> = [\n"
    out_all += out_domains;
    out_all += "    ].iter().copied().collect();\n}\n"

    print(out_all)
