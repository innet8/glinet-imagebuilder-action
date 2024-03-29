#!/usr/bin/env python

import re
import os
import sys
import json
import getopt
import commands
import time
import platform
import hashlib
from subprocess import check_call
from subprocess import check_output

gl_inet_imagebuilder_url = "https://github.com/gl-inet-builder/"
gl_inet_ipks_url = "https://github.com/gl-inet/glinet.git"


def usage(pname):
    print("GL.iNet imagebuilder tool")
    print("Usage: " + pname + " [OPTIONS]")
    print("")
    print(" -a|--all            Build all images from the specified profiles in images.json")
    print(" -p|--profile        Build a specified image from the specified profiles")
    print(" -e|--extra          Extra packages allows to include and/or exclude packages")
    print(" -b|--branch         Change package branch. Default: develop")
    print(" -l|--list           List all available profiles")
    print(" -i|--ignore         Ignore private ipk update from glinet repo")
    print(" -n|--clean          Remove images and temporary build files")
    print(" -c|--config         User-defined configuration file")
    print(" -h|--help           Show this text message")
    print(" -o|--output         Get firmware info, firmware name/md5sum/size")
    print(" --offline           Ignore opensource ipk update")
    print("")
    print("Example: ")
    print(" \
    The following command compiles a firmware for mifi with basic packages and\n \
    extra package(openssh-sftp-server, nano, htop), using images.json as default\n \
    configuration file.\n \
            ")
    print("")
    print("    python2.7 gl_image -p mifi -e \"openssh-sftp-server nano htop\"")
    print("")

    sys.exit(1)


def CleanupGlinetTmpFile(f):
    tmpfile = ""
    if os.path.exists(f + "/repositories.conf"):
        file = open(f + "/repositories.conf")
        for line in file.readlines():
            line = line.strip('\n')
            if "src glinet file:glinet/" in line:
                tmpfile = line.split(':', 1)[1] + "/Packages.*"
                file.close()
                break
    if tmpfile != "":
        os.system(r"rm %s" % tmpfile)


def GetMd5Sum(file_name):
    with open(file_name) as file_to_check:
        data = file_to_check.read()
        md5sum = hashlib.md5(data).hexdigest()
        return md5sum


def GetFirmwareInfo(f, config):
    c = Config(config)
    files = os.listdir(f)
    files.sort()
    str_model = "model"
    str_firmware_name = "firmware name"
    str_firmware_md5sum = "md5sum"
    str_firmware_size = "size"
    str_ib = "imagebuilder version"
    print("%14s  %-40s %-34s %-10s %-30s" % (str_model, str_firmware_name,
          str_firmware_md5sum, str_firmware_size, str_ib))
    for file in files:
        subfiles = os.listdir(f + "/" + file)
        subfiles.sort(reverse=True)
        md5sum = GetMd5Sum(f + "/" + file + "/" + subfiles[0])
        ib = c.getImagebuilderPath(file)
        print("%14s  %-40s %-34s %-10s %-30s" % (file, subfiles[0], md5sum, str(
            os.path.getsize(f + "/" + file + "/" + subfiles[0])), ib))
        # t_path = os.path.join(f, file)
        # if not os.path.isdir(t_path):
        #     # print('file: %s'%t_path)
        #     md5sum = GetMd5Sum(t_path)
        #     print(os.path.basename(t_path) + " " + md5sum + " " + str(os.path.getsize(t_path)))
        # else:
        #     # print('folder: %s'%t_path)
        #     print('\n')
        #     print(os.path.basename(t_path))
        #     GetFirmwareInfo(t_path)


class Config:
    def __init__(self, filename):
        self.filename = filename
        self.parse()

    def parse(self):
        self.data = {}

        try:
            with open(self.filename) as fd:
                self.data = json.load(fd)
                fd.close()
        except:
            print "Oops! Failed to parse %s" % self.filename
            sys.exit(1)

    def dump(self):
        print "%s" % self.data

    def imagesList(self):
        if self.data.has_key("profiles"):
            return self.data["profiles"].keys()

    def getProduct(self, name):
        if self.data["profiles"][name].has_key("product"):
            return self.data["profiles"][name]["product"]

    def getDisabled(self, name):
        if self.data["profiles"][name].has_key("disabled"):
            return self.data["profiles"][name]["disabled"]
        else:
            return False

    def getType(self, name):
        if self.data["profiles"][name].has_key("type"):
            return self.data["profiles"][name]["type"]
        else:
            return "2C"

    def getState(self, name):
        if self.data["profiles"][name].has_key("state"):
            return self.data["profiles"][name]["state"]
        else:
            return "testing"

    def getProfile(self, name):
        if self.data["profiles"][name].has_key("profile"):
            return self.data["profiles"][name]["profile"]

    def getVersion(self, name):
        if self.data["profiles"][name].has_key("version"):
            return self.data["profiles"][name]["version"]

    def getImagebuilderPath(self, name):
        if self.data["profiles"][name].has_key("imagebuilder"):
            return name

    def getImagebuilderVersion(self, name):
        if self.data["profiles"][name].has_key("imagebuilder"):
            return self.data["profiles"][name]["imagebuilder"].split('/', 1)[0]

    def getImagebuilderName(self, name):
        if self.data["profiles"][name].has_key("imagebuilder"):
            return self.data["profiles"][name]["imagebuilder"].split('/', 1)[1]

    def getRepoUrl(self, name):
        url = ""
        if self.data["profiles"][name].has_key("imagebuilder"):
            url = gl_inet_imagebuilder_url + \
                self.data["profiles"][name]["imagebuilder"].split(
                    '/', 1)[1] + ".git"
        return url

    def downloadImagebuilder(self, name, save_dir):
        url = ""
        if self.data["profiles"][name].has_key("imagebuilder"):
            url = gl_inet_imagebuilder_url + \
                self.data["profiles"][name]["imagebuilder"].split(
                    '/', 1)[1] + ".git"

        if url:
            check_call("git clone %s %s" % (url, save_dir), shell=True)

    def getPackages(self, name):
        packages = ""

        if self.data["profiles"][name].has_key("packages"):
            # Convert string to list
            pkg_list = self.data["profiles"][name]["packages"].split(' ')
            for pkg in pkg_list:
                pkg_var = re.search(r'^\$(.*)', pkg)
                if pkg_var and (pkg_var.group() == "$ui4.0" or pkg_var.group() == "$glinet4.0"):
                    continue
                if pkg_var and self.data.has_key("packages"):
                    for (k, v) in self.data["packages"].items():
                        if k == pkg_var.group(1):
                            packages = packages + " " + v
                elif pkg_var is None:
                    packages = packages + " " + pkg

        return packages

    def getFilesPath(self, name):
        if self.data["profiles"][name].has_key("files"):
            return self.data["profiles"][name]["files"]


def show_images(images=[]):
    if images:
        print "User-defined Profiles:\n"
        for img in images:
            print "  %s" % img
    else:
        print "No any profile found"


makeIndex = re.sub('[\t\n ]+', ' ', """
        makeIndex() {
            local topdir=$PWD;
            local script_dir=${topdir}/scripts;
            export PATH="${topdir}/staging_dir/host/bin:${PATH}";
            if [ -z $PKG_PATH ] || [ ! -d $PKG_PATH ]; then
                return 1;
            fi;

            (
                cd $PKG_PATH && [ -n "$(find . -maxdepth 1 -name "*.ipk")" ] || exit 1;

                if [ ! -f "Packages" ] || [ ! -f "Packages.gz" ] || [ "`find . -cnewer Packages.gz`" ]; then

                    echo "Generating package index...";

	            ${script_dir}/ipkg-make-index.sh . 2>&1 > Packages.manifest;
	            grep -avE '^(Maintainer|LicenseFiles|Source|Require)' Packages.manifest > Packages && \
                            gzip -9nc Packages > Packages.gz;

                    return 1;
                fi;
            )
        }
""").strip()


def merge_files(src_dir, dst_dir):
    if os.path.isdir(src_dir) and os.path.isdir(dst_dir):
        check_output("cp -fr %s/* %s/" %
                     (src_dir.rstrip('/'), dst_dir.rstrip('/')), shell=True)


def create_files(im_path, board, ver, dev_type):
    if not im_path or not board or not ver:
        return 1

    tmpfiles = im_path + "/tmp/files"

    # Remove directory
    check_output("rm -fr %s" % tmpfiles, shell=True)

    # Create directory
    check_output("mkdir -p %s" % (tmpfiles + "/etc"), shell=True)
    check_output("mkdir -p %s" % (tmpfiles + "/etc/opkg"), shell=True)

    # glversion
    check_output("echo %s > %s" %
                 (ver, tmpfiles + "/etc/glversion"), shell=True)

    # glproduct
    if dev_type:
        check_output("echo %s > %s" %
                     (dev_type, tmpfiles + "/etc/glproduct"), shell=True)

    # version.date
    # check_output("echo %s > %s" % (output, tmpfiles+ "/etc/version.date"), shell=True)
    compile_time = time.strftime(
        '%Y-%m-%d %k:%M:%S', time.localtime(time.time()))
    check_output("echo %s > %s" %
                 (compile_time, tmpfiles + "/etc/version.date"), shell=True)

    # distfeeds
    try:
        check_output("cat repositories.conf | grep -E \"^src/gz\" > %s" %
                     (tmpfiles + "/etc/opkg/distfeeds.conf"), shell=True, cwd=im_path)
        check_output("cat repositories.conf | \
                grep -E \"gli_pub\" | \
                sed \"s/gli_pub/glinet/g\" >> %s" %
                     (tmpfiles + "/etc/opkg/distfeeds.conf"), shell=True, cwd=im_path)
    except:
        pass

    return tmpfiles

def download_custom_ipk(imageName, path,board):
    import shutil
    for root, dirs, files in os.walk(os.getcwd()+'/'+board):
        for file in files:
            src_file = os.path.join(root, file)
            shutil.copy(src_file, path+"/packages/")
    for root, dirs, files in os.walk(os.getcwd()+'/hiui'):
        for file in files:
            src_file = os.path.join(root, file)
            shutil.copy(src_file, path+"/packages/")
    return

def main(argv):
    # if os.path.exists("files") == False:
    #     os.system('mkdir -p files/etc')
    # os.system('date "+%k:%M:%S %F" > files/etc/version.date')
    pname = argv[0]

    try:
        (opts, args) = getopt.getopt(argv[1:],
                                     "ap:e:b:f:c:lniho:j:",
                                     ["all", "profile=", "extra=", "branch=", "files=", "config=", "list", "clean", "ignore", "help", "output", "offline", "json=", "version="])
    except getopt.GetoptError as e:
        usage(pname)

    extra_ipks = ""
    branch = "v3.215_ap1300/ar150/ar300m/ar750/ar750s/b1300/b2200/e750/mifi/mt1300/mt300n-v2/mv1000-emmc/n300/s1300/sf1200/sft1200/usb150/x300b/x750/xe300"
    ignore = False
    clean = False
    update = False
    show = False
    offline = False
    profile = ""
    filename = "glinet/images.json"
    files = ""
    build_all = False
    images = []
    version = ''

    for (o, v) in opts:
        if o in ("-a", "--all"):
            build_all = True
        if o in ("-p", "--profile"):
            profile = v
        if o in ("-e", "--extra"):
            extra_ipks = v
        if o in ("-b", "--branch"):
            branch = v
        if o in ("-f", "--files"):
            files = v
        if o in ("-c", "--config"):
            filename = v
        if o in ("-l", "--list"):
            show = True
        if o in ("-u", "--update"):
            # Internal variable, use to update repository.conf file
            update = True
        if o in ("-i", "--ignore"):
            ignore = True
        if o in ("-n", "--clean"):
            clean = True
        if o in ("--offline"):
            offline = True
        if o in ("-h", "--help"):
            usage(pname)
        if o in ("-o", "--output"):
            GetFirmwareInfo(os.getcwd() + "/bin", filename)
            sys.exit(1)
        if o in ("-j", "--json"):
            filename = v
        if o in ("--version"):
            version = v

    dir_name = "glinet"
    curpwd = os.getcwd()
    # print("=======================================",offline)
    if not os.path.isdir(dir_name):
        check_call("git clone -b %s --depth=1 %s %s" %
                    (branch, gl_inet_ipks_url, dir_name), shell=True)
    # check_call("git clone  %s %s" %
    #            (gl_inet_ipks_url, dir_name), shell=True)

    c = Config(filename)

    if show:
        show_images(c.imagesList())
        return 0

    # If WSL, Fix PATH variable (Required for building QSDK)
    if ('microsoft' in platform.uname()[3].lower()):
        print('WSL detected, fixed PATH')
        os.environ['PATH'] = ':'.join(
            [r for r in os.environ['PATH'].split(':') if not r.startswith('/mnt')])

    if build_all:
        images = c.imagesList()
    elif profile:
        images.append(profile)
    else:
        usage(pname)

    if not ignore:
        print("Update glinet repository ......")
        check_call("git pull", shell=True, cwd=dir_name)

    if clean:
        for image in images:
            im_path = os.getcwd() + "/imagebuilder/" + c.getImagebuilderPath(image)
            check_call("make clean", shell=True, cwd=im_path)

        return 0

    for image in images:
        if c.getDisabled(image):
            print("\n"+image + "has disabled,Ignored!\n")
            continue
        if c.getImagebuilderVersion(image) != c.getImagebuilderName(image).split('_')[len(c.getImagebuilderName(image).split('_')) - 1]:
            print("\nVersion error! Please check if the " + image +
                  " 's imagebuilder path is correct in json config.\n")
            return 0

        im_save_dir = "imagebuilder/" + c.getImagebuilderVersion(image)
        if not os.path.isdir(im_save_dir):
            check_call("mkdir -p %s" % im_save_dir, shell=True)

        # Search imagebuilder path
        im_path = os.getcwd() + "/imagebuilder/" + c.getImagebuilderPath(image)
        
        # Clean up glinet tmp file Packages/Packages.gz/Packages.manifest
        CleanupGlinetTmpFile(im_path)
        
        if not os.path.isdir(im_path):
            c.downloadImagebuilder(
                image, "imagebuilder/" + c.getImagebuilderPath(image))

        # Make index for glinet
        os.environ["TOPDIR"] = im_path
        try:
            board = check_output(
                "make -f rules.mk val.BOARD V=s 2>/dev/null", shell=True, cwd=im_path).strip()
        except:
            print("Makefile missing...")
            continue

        env = {"PKG_PATH": "%s/glinet/%s" % (os.getcwd(), board)}
        try:
            print(makeIndex,env)
            check_call(['/bin/sh', '-c', '%s; if makeIndex; then makeIndex; fi'
                        % makeIndex], env=env, cwd=im_path)
        except:
            print("Failed to update glinet...")
            continue

        # Offline mode
        if c.getProfile(image) != "QSDK_Premium":
            if offline:
                check_call("cp %s/glinet/%s/Packages dl/glinet" %
                           (os.getcwd(), board), shell=True, cwd=im_path)
                check_call("cp packages/Packages dl/imagebuilder",
                           shell=True, cwd=im_path)
                check_call(
                    "sed -i 's/$(OPKG) update/# $(OPKG) update/g' Makefile", shell=True, cwd=im_path)
                check_call(
                    "sed -i 's/#.*\s*$(OPKG) update/# $(OPKG) update/g' Makefile", shell=True, cwd=im_path)
            else:
                print(im_path)
                check_call(
                    "sed -i 's/#\s.*$(OPKG) update/$(OPKG) update/g' Makefile", shell=True, cwd=im_path)

        # Create link
        glinet_dir = "%s/glinet" % os.getcwd()
        check_call("rm -fr glinet 2>/dev/null", shell=True, cwd=im_path)
        check_call("ln -sf %s glinet 2>/dev/null" %
                   glinet_dir, shell=True, cwd=im_path)

        # Prepare files
        tmpfiles = create_files(
            im_path, board, c.getVersion(image) if version=="" else version, c.getProduct(image))
        if c.getFilesPath(image):
            merge_files(c.getFilesPath(image), tmpfiles)

        if files:
            merge_files(files, tmpfiles)

        # Download custom ipk
        download_custom_ipk(c.getImagebuilderName(image), im_path,board)

        # Output directory
        compile_time = time.strftime('%Y%m%d', time.localtime(time.time()))
        if c.getType(image) == "2B":
            bin_dir = os.getcwd() + "/bin/" + compile_time + "/2B/" + image
        else:
            bin_dir = os.getcwd() + "/bin/" + compile_time + "/" + image

        if not os.path.isdir(bin_dir):
            check_output("mkdir -p %s" % bin_dir, shell=True)

        try:
            check_call("echo %s > release" %
                       (c.getVersion(image) if version=="" else version), shell=True, cwd=im_path)
            os.environ['OFFLINE'] = str(offline)
            check_call("make image \
                    PROFILE=%s \
                    PACKAGES=\"%s\" \
                    FILES=%s \
                    EXTRA_IMAGE_NAME=%s"
                       % (c.getProfile(image), '{} {}'.format(c.getPackages(image), extra_ipks), tmpfiles, image),
                       shell=True, cwd=im_path)
            if c.getState(image) == "develop":
                os.system("echo 'Pls do not use the firmwares in this folder until this file is removed.' >  " +
                          bin_dir + "/Do\ not\ use\ until\ this\ file\ is\ removed.txt")
            else:
                os.system(
                    "rm " + bin_dir + "/Do\ not\ use\ until\ this\ file\ is\ removed.txt 2>/dev/null")
            if c.getProfile(image) == "QSDK_Premium":
                if image == "b1300" or image == "b1300_2b":
                    check_call("find single_img_dir/ -name b1300-nor-apps.img | xargs cp -t %s/"
                               % (bin_dir), shell=True, cwd=im_path)

                    return_code, output = commands.getstatusoutput(
                        "find %s -name b1300-nor-apps.img" % bin_dir)
                    if output != "":
                        fw_name = bin_dir + "/" + "qsdk-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                        os.system('mv ' + output + '  '+curpwd)
                elif image == "s1300":
                    check_call("find single_img_dir/ -name s1300-noremmc-apps.img | xargs cp -t %s/"
                               % (bin_dir), shell=True, cwd=im_path)

                    return_code, output = commands.getstatusoutput(
                        "find %s -name s1300-noremmc-apps.img" % bin_dir)
                    if output != "":
                        fw_name = bin_dir + "/" + "qsdk-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                        os.system('mv ' + output + '  '+curpwd)
                elif image == "ap1300":
                    check_call("find single_img_dir/ -name ap1300-nornand-apps.img | xargs cp -t %s/"
                               % (bin_dir), shell=True, cwd=im_path)

                    return_code, output = commands.getstatusoutput(
                        "find %s -name ap1300-nornand-apps.img" % bin_dir)
                    if output != "":
                        fw_name = bin_dir + "/" + "qsdk-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                        os.system('mv ' + output + '  '+curpwd)
                elif image == "b2200":
                    check_call("find single_img_dir/ -name b2200-noremmc-apps.img | xargs cp -t %s/"
                               % (bin_dir), shell=True, cwd=im_path)

                    return_code, output = commands.getstatusoutput(
                        "find %s -name b2200-noremmc-apps.img" % bin_dir)
                    if output != "":
                        fw_name = bin_dir + "/" + "qsdk-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                        os.system('mv ' + output + '  '+curpwd)
                elif image == "ax1800":
                    check_call("find single_img_dir/ -name ax1800-nand-apps.img | xargs cp -t %s/"
                               % (bin_dir), shell=True, cwd=im_path)

                    return_code, output = commands.getstatusoutput(
                        "find %s -name ax1800-nand-apps.img" % bin_dir)
                    if output != "":
                        fw_name = bin_dir + "/" + "qsdk-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                        os.system('mv ' + output + '  '+curpwd)
                else:
                    check_call("find single_img_dir/ -maxdepth 1 -name *.img | xargs cp -t %s/"
                               % (bin_dir), shell=True, cwd=im_path)

                print(
                    "------------------------------------------------------------------------")
                print("Copy " + output + " to " + fw_name)

            elif image == "mv1000-emmc":
                check_call("find bin/ -name \"*%s-squashfs-emmc*\" | xargs cp -t %s/"
                           % (c.getProfile(image).lower(), bin_dir), shell=True, cwd=im_path)
                return_code, output = commands.getstatusoutput(
                    "find bin/ -name \"*-%s-squashfs-emmc*\"" % (c.getProfile(image).lower()))
                if filename != "glinet/images.json":
                    fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                        c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                  time.localtime()) + os.path.splitext(output)[-1]
                else:
                    fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                        c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                  time.localtime()) + os.path.splitext(output)[-1]
                if output != "":
                    os.system('mv ' + output + '  '+curpwd)

                print(
                    "------------------------------------------------------------------------")
                print("Copy " + output + " to " + fw_name)

            elif c.getProfile(image).find('SF19A28') != -1:
                if image == "sft1200":
                    check_call("find bin/ -name \"*%s-squashfs-sysupgrade*\" | xargs cp -t %s/" %
                               (image, bin_dir), shell=True, cwd=im_path)
                    return_code, output = commands.getstatusoutput(
                        "find bin/ -name \"*-%s-squashfs-sysupgrade*\"" % (image))

                    if filename != "glinet/images.json":
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    else:
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    if output != "":
                        os.system('mv ' + output + '  '+curpwd)

                    print(
                        "------------------------------------------------------------------------")
                    print("Copy " + output + " to " + fw_name)

                    check_call("find bin/ -name \"*%s*squashfs-factory*\" | xargs cp -t %s/" %
                               (image, bin_dir), shell=True, cwd=im_path)
                    return_code, output = commands.getstatusoutput(
                        "find bin/ -name \"*%s*squashfs-factory*\"" % (image))
                    if filename != "glinet/images.json":
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    else:
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    if output != "":
                        os.system('mv ' + output + '  '+curpwd)

                    print(
                        "------------------------------------------------------------------------")
                    print("Copy " + output + " to " + fw_name)
                else:
                    check_call("find bin/ -name \"*%s-siflower-sf19a28-fullmask-squashfs-sysupgrade*\" | xargs cp -t %s/"
                               % (image, bin_dir), shell=True, cwd=im_path)
                    return_code, output = commands.getstatusoutput(
                        "find bin/ -name \"*-%s-siflower-sf19a28-fullmask-squashfs-sysupgrade*\"" % (image))

                    if filename != "glinet/images.json":
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    else:
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    if output != "":
                        os.system('mv ' + output + '  '+curpwd)

                    print(
                        "------------------------------------------------------------------------")
                    print("Copy " + output + " to " + fw_name)

            else:
                # print(c.getProfile(image))
                # print(image)
                check_call("find bin/ -name \"*%s-squashfs-sysupgrade*\" | xargs cp -t %s/"
                           % (c.getProfile(image).lower(), bin_dir), shell=True, cwd=im_path)
                return_code, output = commands.getstatusoutput(
                    "find bin/ -name \"*-%s-squashfs-sysupgrade*\"" % (c.getProfile(image).lower()))
                if filename != "glinet/images.json":
                    fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                        c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                  time.localtime()) + os.path.splitext(output)[-1]
                else:
                    fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                        c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                  time.localtime()) + os.path.splitext(output)[-1]
                if output != "":
                    os.system('mv ' + output + '  '+curpwd)

                print(
                    "------------------------------------------------------------------------")
                print("Copy " + output + " to " + fw_name)

                if c.getProfile(image).find('nand') != -1 or c.getProfile(image).find('xe300-iot') != -1 or c.getProfile(image).find('axt1800') != -1:
                    if image == "e750-1907":
                        check_call("find bin/ -name \"*%s*squashfs-factory*\" | xargs cp -t %s/" %
                                   (image, bin_dir), shell=True, cwd=im_path)
                        return_code, output = commands.getstatusoutput(
                            "find bin/ -name \"*%s*squashfs-factory*\"" % (c.getProfile(image).lower()))
                    # else image == "xe300":
                    else:
                        check_call("find bin/ -name \"*%s*-factory.img\" | xargs cp -t %s/" %
                                   (image, bin_dir), shell=True, cwd=im_path)
                        return_code, output = commands.getstatusoutput(
                            "find bin/ -name \"*%s*-factory.img\"" % (c.getProfile(image).lower()))

                    if filename != "glinet/images.json":
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    else:
                        fw_name = bin_dir + "/" + "openwrt-" + image + "-" + \
                            c.getVersion(image) + "-" + time.strftime("%m%d",
                                                                      time.localtime()) + os.path.splitext(output)[-1]
                    if output != "":
                        os.system('mv ' + output + '  '+curpwd)
                        print("Copy " + output + " to " + fw_name)

        except:
            print("Failed to build %s..." % c.getProfile(image))
            continue


if __name__ == "__main__":
    sys.exit(main(sys.argv))
  
