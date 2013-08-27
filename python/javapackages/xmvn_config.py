#!/usr/bin/python
# Copyright (c) 2013, Red Hat, Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.
# 3. Neither the name of Red Hat nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Authors:  Stanislav Ochotnicky <sochotnicky@redhat.com

import codecs
import os
from StringIO import StringIO
import xml.dom.minidom

import lxml.etree as ET
from lxml.etree import ElementTree, Element, SubElement


class XMvnConfig(object):
    """
    Class for modifying XMvn configuration
    """

    INDEX_PATH = os.path.join(".xmvn", "javapackages-rule-index")
    CONFIG_DIR = os.path.join(".xmvn", "config.d")
    XMLNS = "http://fedorahosted.org/xmvn/CONFIG/0.6.0"

    def __init__(self):
        self.templateXML ="""<?xml version='1.0' encoding='utf-8'?>
<configuration xmlns="http://fedorahosted.org/xmvn/CONFIG/0.6.0">
{content}
</configuration>
"""
        try:
            with open(XMvnConfig.INDEX_PATH) as index:
                self.index = int(index.read()) + 1
        except IOError:
            os.makedirs(".xmvn/config.d", 0755)
            self.index = 1

    def __write_index(self):
        with open(XMvnConfig.INDEX_PATH, 'w') as index:
            index.write(str(self.index))
            self.index = self.index + 1

    def __get_current_config(self):
        fname = 'javapackages-config-{index:05d}.xml'.format(index=self.index)
        return os.path.join(XMvnConfig.CONFIG_DIR,
                            fname)

    def __init_xml(self, content=""):
        self.__write_index()

        xmlbuf = StringIO()
        xmlbuf.write(self.templateXML.format(content=content))

        root = ET.fromstring(xmlbuf.getvalue())
        root.append(ET.Comment("XMvn configuration file generated by "
                               "javapackages.xmvn_config  (part of "
                               "javapackages-tools)"))
        return root

    def __prettify_element(self, elem):
        xmlbuf = StringIO()
        et = ElementTree()
        et._setroot(elem)
        et.write(xmlbuf,
                 xml_declaration=True,
                 encoding = 'utf-8',
                 method = "xml")
        return xml.dom.minidom.parseString(xmlbuf.getvalue()).toprettyxml()


    def __write_xml(self, path, root):
        xmlstr = self.__prettify_element(root)
        with codecs.open(path, 'w+', "utf-8") as fout:
            fout.write(xmlstr)


    def __add_config(self, level1, level2, level3=None, content=None):
        if not content:
            raise Exception("Provide content as keyword argument")

        confpath = self.__get_current_config()
        root = self.__init_xml()

        level1 = SubElement(root, level1)
        level2 = SubElement(level1, level2)
        cont_level = level2
        if level3:
            cont_level = SubElement(level2, level3)

        if isinstance(content, basestring):
            cont_level.text = content
        elif isinstance(content, list):
            for elem in content:
                cont_level.append(elem)
        else:
            cont_level.append(content)

        self.__write_xml(confpath, root)


    def add_aliases(self, artifact, aliases):
        """
        Adds alias artifacts for given main artifact

        artifact -- main Artifact for which aliases are being provided
        aliases -- list of alternate Artifact representations
        """
        elems = [artifact.get_xml_element(root="artifactGlob")]
        aelem = Element("aliases")
        for alias in aliases:
            aelem.append(alias.get_xml_element(root="alias"))
        elems.append(aelem)
        self.__add_config("artifactManagement", "rule", content=elems)

    def add_file_mapping(self, artifact, paths):
        """
        Change where on filesystem given artifact is installed

        artifact -- Artifact to be modified
        paths -- list of paths for given artifact
        """
        elems = [artifact.get_xml_element(root="artifactGlob")]
        felem = Element("files")
        for path in paths:
            pe = SubElement(felem, "file")
            pe.text = path
        elems.append(felem)
        self.__add_config("artifactManagement", "rule", content=elems)

    def add_package_mapping(self, artifact, package):
        """
        Change which package given artifact belongs to

        artifact -- Artifact to be modified
        package -- subpackage name where artifact belongs
        """
        elems = [artifact.get_xml_element(root="artifactGlob")]
        target = Element("targetPackage")
        target.text = package
        elems.append(target)
        self.__add_config("artifactManagement", "rule", content=elems)

    def add_custom_option(self, optionstr, content):
        """
        Add custom configuration option

        optionstr -- XPath-like expression for specifying XMvn configuration
                     option location with '/' used as delimiter

                     example: buildSettings/compilerSource
        content -- text to which the option will be set (no XML allowed)
        """
        node_names = optionstr.split("/")
        confpath = self.__get_current_config()
        root = self.__init_xml()
        par = root
        for node in node_names:
            par = SubElement(par, node)

        par.text = content
        self.__write_xml(confpath, root)
