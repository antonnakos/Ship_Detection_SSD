import lxml.etree
import random
import math
import cv2
import os

import numpy as np

from utils import Label, Box, Sample, Size
from utils import rgb2bgr, abs2prop
from glob import glob
from tqdm import tqdm

#-------------------------------------------------------------------------------
# Labels
#-------------------------------------------------------------------------------
label_defs = [
    Label('ship',   rgb2bgr((150, 20, 0))),
    ]

#-------------------------------------------------------------------------------
class SarShipSource:
    #---------------------------------------------------------------------------
    def __init__(self):
        self.num_classes   = len(label_defs)
        self.colors        = {l.name: l.color for l in label_defs}
        self.lid2name      = {i: l.name for i, l in enumerate(label_defs)}
        self.lname2id      = {l.name: i for i, l in enumerate(label_defs)}
        self.num_train     = 0
        self.num_valid     = 0
        self.num_test      = 0
        self.train_samples = []
        self.valid_samples = []
        self.test_samples  = []

    #---------------------------------------------------------------------------
    def __build_annotation_list(self, root, dataset_type):
        """
        Build a list of samples for the VOC dataset (either trainval or test)
        """
        annot_root  = root + '/Annotations/'
        annot_files = []
        with open(root + '/ImageSets/Main/' + dataset_type + '.txt') as f:
            for line in f:
                annot_file = annot_root + line.strip() + '.xml'
                if os.path.exists(annot_file):
                    annot_files.append(annot_file)
        return annot_files

    #---------------------------------------------------------------------------
    def __build_sample_list(self, root, annot_files, dataset_name):
        """
        Build a list of samples for the VOC dataset (either trainval or test)
        """
        image_root  = root + '/JPEGImages/'
        samples     = []

        #-----------------------------------------------------------------------
        # Process each annotated sample
        #-----------------------------------------------------------------------
        for fn in tqdm(annot_files, desc=dataset_name, unit='samples'):
            with open(fn, 'r') as f:
                doc      = lxml.etree.parse(f)
                filename = image_root+doc.xpath('/annotations/filename')[0].text

                #---------------------------------------------------------------
                # Get the file dimensions
                #---------------------------------------------------------------
                #if not os.path.exists(filename):
                 #   continue

                img     = cv2.imread(filename)
                imgsize = Size(img.shape[1], img.shape[0])

                #---------------------------------------------------------------
                # Get boxes for all the objects
                #---------------------------------------------------------------
                boxes    = []
                objects  = doc.xpath('/annotations/object')
                for obj in objects:
                    #-----------------------------------------------------------
                    # Get the properties of the box and convert them to the
                    # proportional terms
                    #-----------------------------------------------------------
                    label = obj.xpath('name')[0].text
                    xmin  = int(float(obj.xpath('bndbox/xmin')[0].text))
                    xmax  = int(float(obj.xpath('bndbox/xmax')[0].text))
                    ymin  = int(float(obj.xpath('bndbox/ymin')[0].text))
                    ymax  = int(float(obj.xpath('bndbox/ymax')[0].text))
                    center, size = abs2prop(xmin, xmax, ymin, ymax, imgsize)
                    box = Box(label, self.lname2id[label], center, size)
                    boxes.append(box)
                if not boxes:
                    continue
                sample = Sample(filename, boxes, imgsize)
                samples.append(sample)

        return samples

    #---------------------------------------------------------------------------
    def load_trainval_data(self, data_dir, valid_fraction):
        """
        Load the training and validation data
        :param data_dir:       the directory where the dataset's file are stored
        :param valid_fraction: what franction of the dataset should be used
                               as a validation sample
        """

        #-----------------------------------------------------------------------
        # Process the samples defined in the relevant file lists
        #-----------------------------------------------------------------------
        train_annot = []
        train_samples = []
        
        root = data_dir + '/trainval'
        name = 'trainval_'
        
        #annot = self.__build_annotation_list(root, 'trainval')
        train_annot = set(glob(root + '/Annotations/train/*.xml'))
        train_samples += self.__build_sample_list(root, train_annot,name)

        

        #-----------------------------------------------------------------------
        # We have some 5.5k annotated samples that are not on these lists, so
        # we can use them for validation
        #-----------------------------------------------------------------------
        root = data_dir + '/trainval/'
        valid_annot = set(glob(root + '/Annotations/val/*.xml'))
        #valid_annot = all_annot - set(train_annot)
        valid_samples = self.__build_sample_list(root, valid_annot, "valid_"
                                                 )

        #-----------------------------------------------------------------------
        # Final set up and sanity check
        #-----------------------------------------------------------------------
        self.valid_samples = valid_samples
        self.train_samples = train_samples

        if len(self.train_samples) == 0:
            raise RuntimeError('No training samples found in ' + data_dir)

        if valid_fraction > 0:
            if len(self.valid_samples) == 0:
                raise RuntimeError('No validation samples found in ' + data_dir)

        self.num_train = len(self.train_samples)
        self.num_valid = len(self.valid_samples)

    #---------------------------------------------------------------------------
    def load_test_data(self, data_dir):
        """
        Load the test data
        :param data_dir: the directory where the dataset's file are stored
        """
        root = data_dir + '/test'
        annot = set(glob(root + '/Annotations/*.xml'))
        self.test_samples  = self.__build_sample_list(root, annot, "test"
                                                      )

        if len(self.test_samples) == 0:
            raise RuntimeError('No testing samples found in ' + data_dir)

        self.num_test  = len(self.test_samples)

#-------------------------------------------------------------------------------
def get_source():
    return SarShipSource()
