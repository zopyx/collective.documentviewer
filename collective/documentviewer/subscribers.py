from logging import getLogger
import os
import shutil
from Products.CMFCore.utils import getToolByName
from collective.documentviewer.settings import GlobalSettings
from collective.documentviewer.settings import Settings
from collective.documentviewer.utils import allowedDocumentType
from collective.documentviewer.utils import getPortal
from collective.documentviewer.async import queueJob
from collective.documentviewer import storage
from collective.documentviewer.convert import Converter

logger = getLogger('collective.documentviewer')


def handle_file_creation(object, event):
    qi = getToolByName(object, 'portal_quickinstaller')
    if not qi.isProductInstalled('collective.documentviewer'):
        return

    site = getPortal(object)
    gsettings = GlobalSettings(site)

    if not allowedDocumentType(object, gsettings.auto_layout_file_types):
        return

    auto_layout = gsettings.auto_select_layout
    if auto_layout and object.getLayout() != 'documentviewer':
        object.setLayout('documentviewer')

    if object.getLayout() == 'documentviewer' and gsettings.auto_convert:
        queueJob(object)


def handle_workflow_change(object, event):
    settings = Settings(object)
    site = getPortal(object)
    gsettings = GlobalSettings(site)
    if not gsettings.storage_obfuscate or \
            settings.storage_type != 'File':
        return
    for perm in object.rolesOfPermission("View"):
        if perm['name'] == 'Anonymous' and perm["selected"] != "":
            # anon can now view, move it to normal
            storage_dir = storage_dir = storage.getResourceDirectory(
                gsettings=gsettings, settings=settings)
            secret_dir = os.path.join(storage_dir,
                                      settings.obfuscate_secret)
            if not os.path.exists(secret_dir):
                # already public, oops
                return
            for folder in os.listdir(secret_dir):
                path = os.path.join(secret_dir, folder)
                newpath = os.path.join(storage_dir, folder)
                shutil.move(path, newpath)
            shutil.rmtree(secret_dir)
            settings.obfuscated_filepath = False
            return
    # if we made it here, the item might have been switched back
    # to being unpublished. Let's just get the converter object
    # and re-move it
    converter = Converter(object)
    converter.handleFileObfuscation()
