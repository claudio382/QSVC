#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

## @file transcode.py
#  Extracts a codestream from a bigger codestream, discarding a number
#  of temporal, resolution or/and quality.\n The number of temporal
#  resolution levels that is going to be discardes must be >= 0 (0 = no
#  discarding).\n Some thing similar happens with the number of discardes
#  spatial resolutions.\n\n The last parameter is controlled by means of a
#  slope, a value between 0 a 65535 where 0 means no discarding and
#  65553 implies a null output video, but notice that if the input
#  video was quantized using a slope X and we select a new slope where
#  Y <= X, then, this extraction will not have any effect (the output
#  will be identical to the input).\n These parameters can not be used
#  simultaneously, but obviously, they can be concatenated. The output
#  sequences will overwrite the input sequences.
#
#  You can perform a direct transcoding. Indicating the number of
#  layers of each subband to extract.
#  
#  You can also make use of one, sorting algorithms, implemented. The
#  organization consists of calculating the optimal order of layers of
#  each subband to be sent from one codestream optimally in term of
#  rate and distortion.
#  
#  There is an algorithm of optimal result, called FS-opt, which has
#  the highest of all algorithmic complexity. Also present, other
#  algorithms, in which the result is suboptimal, but have lower
#  algorithmic complexity.
#  
#  There are 2 types of sorting algorithms:
#  - Manages the full video
#  - Manages the video GOP to GOP
#
#  This depends, of sorting algorithm, which is being conducted. For
#  example, in the Full-Search algorithm, the calculations are
#  independent of each different GOP therefore should be treated to
#  GOP GOP.
#
#  @authors Jose Carmelo Maturana-Espinosa\n Vicente Gonzalez-Ruiz.
#  @date Last modification: 2015, January 7.
#
#  @example transcode.py
#
#  - Divides the frame-rate by two.\n
#  mcj2k transcode --discard_TRLs=1
#
#  - Divides the spatial resolution of the video by 2^2 in each dimmension.\n
#  mcj2k transcode --discard_SRLs=2
#
#  - Outputs only the first GOP (only one image).\n
#  mcj2k transcode --GOPs=1
#
#  - Example of use.\n 
#  mcj2k transcode --algorithm=FS-opt --update_factor=0 --GOPs=8 --TRLs=5 --SRLs=4
#  --FPS=50 --BRC=500000 --discard_SRLs=0 --pixels_in_x=352
#  --pixels_in_y=288 --block_size=32 --search_range=4 --nLayers=16

## @package transcode
#  Extracts a codestream from a bigger codestream, discarding a number
#  of temporal, resolution or/and quality.\n The number of temporal
#  resolution levels that is going to be discardes must be >= 0 (0 = no
#  discarding).\n Some thing similar happens with the number of discardes
#  spatial resolutions.\n\n The last parameter is controlled by means of a
#  slope, a value between 0 a 65535 where 0 means no discarding and
#  65553 implies a null output video, but notice that if the input
#  video was quantized using a slope X and we select a new slope where
#  Y <= X, then, this extraction will not have any effect (the output
#  will be identical to the input).\n These parameters can not be used
#  simultaneously, but obviously, they can be concatenated. The output
#  sequences will overwrite the input sequences.
#
#  You can perform a direct transcoding. Indicating the number of
#  layers of each subband to extract.
#  
#  You can also make use of one, sorting algorithms, implemented. The
#  organization consists of calculating the optimal order of layers of
#  each subband to be sent from one codestream optimally in term of
#  rate and distortion.
#  
#  There is an algorithm of optimal result, called FS-opt, which has
#  the highest of all algorithmic complexity. Also present, other
#  algorithms, in which the result is suboptimal, but have lower
#  algorithmic complexity.
#  
#  There are 2 types of sorting algorithms:
#  - Manages the full video
#  - Manages the video GOP to GOP
#
#  This depends, of sorting algorithm, which is being conducted. For
#  example, in the Full-Search algorithm, the calculations are
#  independent of each different GOP therefore should be treated to
#  GOP GOP.



import info_j2k
import sys
import getopt
import os
import array
import display
import string
import math
import re
import subprocess as sub
from GOP          import GOP
from subprocess   import check_call
from subprocess   import CalledProcessError
from MCTF_parser  import MCTF_parser


## Refers to high frequency subbands.
HIGH              = "high_"
## Refers to low frequency subbands.
LOW               = "low_"
## Refers to fields of motion.
MOTION            = "motion_residue_"
## Number of components in the fields of motion.
MOTION_COMPONENTS = 4
## A very high value. It's useful to use in a given iteration of
## comparisons.
MAX_VALUE         = 2000000000
## Number of Group Of Pictures to process.
GOPs              = 1
## Number of Temporal Resolution Levels.
TRLs              = 4
## Number of Spatial Resolution Levels.
SRLs              = 5
## Maximum available bandwidth. The Full-Search algorithm calculates
## the optimal order of layers, up to this value. Its default value is
## very high, therefore, if a value is not specified, the order of all
## layers of the codestream is calculated.
BRC               = MAX_VALUE
## Number of levels of temporal resolution discarded.
discard_TRLs      = 0
## Number of levels of spatial resolution discarded for each subband.
discard_SRLs      = "0,0,0,0,0,0,0,0,0"
## Width of the pictures.
pixels_in_x       = 352   # 352  # 1920
## Height of the pictures.
pixels_in_y       = 288   # 288  # 1088
## Frames per second.
FPS               = 30    # 30   # 50
## Size of the blocks in the motion estimation process.
block_size        = 32    # 32   # 64
## Minimal block size allowed in the motion estimation process.
block_size_min    = 32    # 32   # 64
## Size of the search areas in the motion estimation process.
search_range      = 4
## Number of quality layers to extract.
nLayers           = 1
## Number of codestream quality layers.
Ncapas_T          = 16
## Weight of the update step.
update_factor     = 1.0/4
## Type sorting algorithm.
algorithm         = ""
## Number of quality layers that are extracted for each subbband.
combination       = ""



## The parser module provides an interface to Python's internal parser
## and byte-code compiler.
parser = MCTF_parser(description="Transcode.")
parser.add_argument("--GOPs", help="number of GOPs to process. (Default = {})".format(GOPs))
parser.add_argument("--TRLs", help="number of iterations of the temporal transform + 1. (Default = {})".format(TRLs))
parser.SRLs(SRLs)
parser.add_argument("--BRC",  help="bit-rate control (kbps). (Default = {})".format(BRC))
parser.add_argument("--discard_TRLs", help="number of discarded temporal resolution levels. (Default = {})".format(discard_TRLs))
parser.add_argument("--discard_SRLs", help="List of discarded spatial resolution levels for textures and motions. Example: for TRL=3 there are 5 discarded, these values correspond to L2, H2, H1, M2 and M1. (Default = {})".format(discard_SRLs))
parser.pixels_in_x(pixels_in_x)
parser.pixels_in_y(pixels_in_y)
parser.FPS(FPS)
parser.block_size(block_size)
parser.search_range(search_range)
parser.add_argument("--nLayers", help="Number of quality layers. (Default = {})".format(nLayers))
parser.update_factor(update_factor)
parser.add_argument("--algorithm", help="Type sorting algorithm. (Default = {})".format(algorithm))
parser.add_argument("--combination", help="Number of quality layers that are extracted for each subbbanda. (Default = {})".format(combination))

## A script may only parse a few of the command-line arguments,
## passing the remaining arguments on to another script or program.
args = parser.parse_known_args()[0]
if args.GOPs :
    GOPs = int(args.GOPs)
if args.TRLs :
    TRLs = int(args.TRLs)
if args.SRLs :
    SRLs = int(args.SRLs)
if args.BRC :
    BRC = int(args.BRC)
if args.discard_TRLs :
    discard_TRLs = int(args.discard_TRLs)
if args.discard_SRLs :
    discard_SRLs = str(args.discard_SRLs)
if args.pixels_in_x :
    pixels_in_x = int(args.pixels_in_x)
if args.pixels_in_y :
    pixels_in_y = int(args.pixels_in_y)
if args.FPS :
    FPS = int(args.FPS)
if args.block_size :
    block_size = int(args.block_size)
if args.search_range :
    search_range = int(args.search_range)
if args.nLayers :
    Ncapas_T = int(args.nLayers)
if args.update_factor :
    update_factor = float(args.update_factor)
if args.algorithm :
    algorithm = str(args.algorithm)
if args.combination :
    combination = str(args.combination)


if BRC > MAX_VALUE :
    BRC = MAX_VALUE - 1






#----------------------------------------------------
#----------------------------------------------------
#- FUNCTIONS ----------------------------------------
#----------------------------------------------------
#----------------------------------------------------


## Determines the size of the header of a codestream.
#  @param file_name Name of the file with the motion fields.
#  @return Bytes of the header of a codestream.
def header (file_name) :
    p = sub.Popen("header_size " + str(file_name) + " 2> /dev/null | grep OUT", shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
    out, err = p.communicate()
    return long(out[4:])




## Transcode a codestream, reducing the bit-rate and quality, by
## extracting a given number of layers of a given subband.
#  @param in_filename File containing a given sub-band component and the codestream. This subband is complete.
#  @param out_filename File containing a given sub-band component and the codestream. This subband is truncated.
#  @param cLayers Number of layers, which are extracted from the entire sub-band for the truncated subband.
#  @param reduces Number of levels of spatial resolution that will be discarded. It is a deprecated option. The optimal results are obtained by extracting layers (scalability in quality). Its default value is 0.
#  @param rate Indicates a bit-rate, whereby the truncated codestream apply. In a scalable codestream in quality, optimal results are obtained to indicate a certain number of layers to extract. Therefore, this option is deprecated. Its default value is 0.
#  @return File size without header.
def kdu_transcode (in_filename, out_filename, cLayers, reduces, rate): # kdu_transcode -usage | less
    try :

        # Transcode by rate.
        #-------------------
        if rate <= 0.0 :

            p = sub.Popen("trace kdu_transcode"
                          + " -i "      + in_filename
                          + " -o "      + "extract/" + out_filename
                          + " Clayers=" + str(cLayers)
                          + " -reduce " + str(reduces)
                          , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
            out, err = p.communicate()

        else :

            # Transcode by Clayers.
            #----------------------

            p = sub.Popen("trace kdu_transcode"
                          + " -i "      + in_filename
                          + " -o "      + "extract/" + out_filename
                          + " Clayers=" + str(cLayers)
                          + " -reduce " + str(reduces)
                          + " -rate "   + str(rate)
                          , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
            out, err = p.communicate()

        # Displays information about the execution:
        # check_call("echo \"OUT: " + str(out) + "\"", shell=True)
        # check_call("echo \"ERR: " + str(err) + "\"", shell=True)


        # Sizes
        #------
        if err != "" : # if err in locals() :
            check_call("rm extract/" + out_filename, shell=True)
            size = 0
        else :
            size = os.path.getsize("extract/" + out_filename) - header("extract/" + out_filename)

        # Displays information about the execution:
        # check_call("echo FILE " + str("extract/" + out_filename) + " SIZE " + str(os.path.getsize("extract/" + out_filename))  + " HEADER " + str(header("extract/" + out_filename)) + " final " + str(size), shell=True) #  !!!!
        # raw_input("")

        return size

    except CalledProcessError :
        sys.exit(-1)

## transcode Select the number of layers, of which component from
## which subband, from which GOP (or set of GOPs) must be
## extracted. Extraction, comes out, the kdu_transcode function.
#
#  Transcoding can be performed:
#  - GOP to GOP.
#  - The full sequence, ie all GOPs.
#
#  This depends, of sorting algorithm, which is being conducted. For
#  example, in the Full-Search algorithm, the calculations are
#  independent of each different GOP therefore should be treated to
#  GOP GOP.
#
#  @param N_subbands Number of subbands the codestream.
#  @param FIRST_picture_ofGOP Number of the first image of the GOP, in the overall sequence of images.
#  @param pictures Total number of images in the sequence.
#  @param _COMBINATION List some specific numbers of layers for each subband.
#  @param _COMBINATION_REDUCES_normalized List certain values of spatial resolution reduction, for each subband. Its default values are zero. Not usually used because, as exploit the scalability provides better results. But it is a useful source for research tasks.
def transcode (N_subbands, FIRST_picture_ofGOP, pictures, _COMBINATION, _COMBINATION_REDUCES_normalized) :

    # Displays information about the execution:
    # check_call("echo _COMBINATION en el transcode: " + str(_COMBINATION), shell=True)
    # check_call("echo N_subbands: " + str(N_subbands), shell=True)
    # raw_input("")


    check_call("  rm -rf " + str(path_extract) + "; "
               + "mkdir "  + str(path_extract)
               , shell=True)


    #  Transcoding can be performed:
    #  - GOP to GOP.
    #  - The full sequence, ie all GOPs.
    if FIRST_picture_ofGOP == 0 :
        transcode_unitario = False # Transcoding: The full sequence, ie all GOPs.
    else :
        transcode_unitario = True  # Transcoding: GOP to GOP. You need to rename the files (in_filename! = Outfilename).


    # MOTIONS.
    #---------
    if TRLs > 1 : # if discard_SRLs_Mot != 0 :

        fields = pictures / 2
        FIRST_fields = FIRST_picture_ofGOP / 2
        subband = 1

        while subband < TRLs :

            if _COMBINATION[N_subbands-subband] != 0 : # If you want to extract some layer of the treated subband in the current iteration.

                # Files sizes. With the size of each component.
                file_sizes = open (str(path_extract) + "/" + MOTION + str(subband) + ".mjc", 'w')
                total = 0

                for campoMov_number in range (FIRST_fields, fields) : # Decode components
                    for comp_number in range (0, MOTION_COMPONENTS) :

                        # Displays information about the execution:
                        # check_call("echo MOTION: comp" + str(comp_number) + " " + str('%04d' % campoMov_number) + " " + str('%04d' % (campoMov_number - FIRST_fields)) , shell=True)

                        out_filename = in_filename = MOTION + str(subband) + "_comp" + str(comp_number) + "_" + str('%04d' % campoMov_number) + ".j2c"
                        if transcode_unitario == True :
                            out_filename           = MOTION + str(subband) + "_comp" + str(comp_number) + "_" + str('%04d' % (campoMov_number - FIRST_fields)) + ".j2c"

                        size = kdu_transcode (in_filename, out_filename, _COMBINATION[N_subbands-subband], _COMBINATION_REDUCES_normalized[N_subbands-subband], 0) #p = sub.Popen("cp " + in_filename + " extract/" + out_filename, shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
                        total += size

                    file_sizes.write(str(total) + "\n")
                file_sizes.close()

            subband += 1
            fields /= 2
            FIRST_fields /= 2



    # TEXTURES.
    #----------


    # HIGH frecuency.
    #----------------
    subband = 1
    while subband < TRLs :

        pictures = (pictures + 1) / 2
        FIRST_picture_ofGOP = FIRST_picture_ofGOP / 2

        # Displays information about the execution:
        # check_call("echo HIGH: sub " + str(subband) + ". De " + str(FIRST_picture_ofGOP) + " a " + str(pictures-2), shell=True) # !


        if _COMBINATION[TRLs-subband] != 0 : # If you want to extract some layer of the treated subband in the current iteration.

            # Files sizes. With the size of each component.
            file_sizes = open (str(path_extract) + "/" + HIGH + str(subband) + ".j2c", 'w')
            total = 0

            image_number = FIRST_picture_ofGOP
            while image_number < (pictures - 1) :

                # Displays information about the execution:
                # check_call("echo HIGH: " + str('%04d' % image_number) + " " + str('%04d' % (image_number - FIRST_picture_ofGOP)) , shell=True) # !

                # Y
                out_filename = in_filename = HIGH + str(subband) + "_Y_" + str('%04d' % image_number) + ".j2c"
                if transcode_unitario == True :
                    out_filename           = HIGH + str(subband) + "_Y_" + str('%04d' % (image_number - FIRST_picture_ofGOP)) + ".j2c"
                Ysize = kdu_transcode (in_filename, out_filename, _COMBINATION[TRLs-subband], _COMBINATION_REDUCES_normalized[TRLs-subband], _RATES_Y[TRLs-subband][int(image_number)])

                # U
                out_filename = in_filename = HIGH + str(subband) + "_U_" + str('%04d' % image_number) + ".j2c"
                if transcode_unitario == True :
                    out_filename           = HIGH + str(subband) + "_U_" + str('%04d' % (image_number - FIRST_picture_ofGOP)) + ".j2c"
                Usize = kdu_transcode (in_filename, out_filename, _COMBINATION[TRLs-subband], _COMBINATION_REDUCES_normalized[TRLs-subband], _RATES_U[TRLs-subband][int(image_number)])

                # V
                out_filename = in_filename = HIGH + str(subband) + "_V_" + str('%04d' % image_number) + ".j2c"
                if transcode_unitario == True :
                    out_filename           = HIGH + str(subband) + "_V_" + str('%04d' % (image_number - FIRST_picture_ofGOP)) + ".j2c"
                Vsize = kdu_transcode (in_filename, out_filename, _COMBINATION[TRLs-subband], _COMBINATION_REDUCES_normalized[TRLs-subband], _RATES_V[TRLs-subband][int(image_number)])

                # Total file-sizes
                size = Ysize + Usize + Vsize
                total += size
                file_sizes.write(str(total) + "\n")

                image_number += 1

                # Displays information about the execution:
                # check_call("echo TRLs: " + str(TRLs) + " subband: " + str(subband) + " List_Clayers[TRLs-subband]: " + str(List_Clayers[TRLs-subband]), shell=True) #  + " >> output" !!!
                # raw_input("Press ENTER to continue ...") # !

            file_sizes.close()
        subband += 1
    subband -= 1



    # LOW frecuency.
    #---------------

    # Displays information about the execution:
    # check_call("echo LOW: sub " + str(subband) + ". De " + str(FIRST_picture_ofGOP) + " a " + str(pictures-1), shell=True) # !

    if _COMBINATION[0] != 0 : # If you want to extract some layer of the treated subband in the current iteration.

        # Files sizes. With the size of each color image.
        file_sizes = open (str(path_extract) + "/" + LOW + str(subband) + ".j2c", 'w')
        total = 0

        image_number = FIRST_picture_ofGOP
        while image_number < pictures:

            # Displays information about the execution:
            # check_call("echo LOW: " + str('%04d' % image_number) + " " + str('%04d' % (image_number - FIRST_picture_ofGOP)) , shell=True) # !

            # Y
            out_filename = in_filename = LOW + str(subband) + "_Y_" + str('%04d' % image_number) + ".j2c"
            if transcode_unitario == True :
                out_filename           = LOW + str(subband) + "_Y_" + str('%04d' % (image_number - FIRST_picture_ofGOP)) + ".j2c"
            Ysize = kdu_transcode (in_filename, out_filename, _COMBINATION[0], _COMBINATION_REDUCES_normalized[0], _RATES_Y[0][0])

            # U
            out_filename = in_filename = LOW + str(subband) + "_U_" + str('%04d' % image_number) + ".j2c"
            if transcode_unitario == True :
                out_filename           = LOW + str(subband) + "_U_" + str('%04d' % (image_number - FIRST_picture_ofGOP)) + ".j2c"
            Usize = kdu_transcode (in_filename, out_filename, _COMBINATION[0], _COMBINATION_REDUCES_normalized[0], _RATES_U[0][0])

            # V
            out_filename = in_filename = LOW + str(subband) + "_V_" + str('%04d' % image_number) + ".j2c"
            if transcode_unitario == True :
                out_filename           = LOW + str(subband) + "_V_" + str('%04d' % (image_number - FIRST_picture_ofGOP)) + ".j2c"
            Vsize = kdu_transcode (in_filename, out_filename, _COMBINATION[0], _COMBINATION_REDUCES_normalized[0], _RATES_V[0][0])

            # Total file-sizes
            size = Ysize + Usize + Vsize
            total += size
            file_sizes.write(str(total) + "\n")

            # Displays information about the execution:
            # check_call("echo TRLs: " + str(TRLs) + " subband: " + str(subband) + " List_Clayers[TRLs-subband]: " + str(List_Clayers[TRLs-subband]), shell=True) #  + " >> output" !!!
            # raw_input("Press ENTER to continue ...") # !

            image_number += 1

        file_sizes.close()





## Number of bytes of an entire directory. The size in bytes, and a
## codestream Kbps, even detailed subband level and neglecting headers
## is performed in info.py.
#  @param the_path Directory path.
#  @param key If you want to have only a certain type of files in the directory.
#  @return Files size.
def get_size (the_path, key) :

    path_size = 0
    for path, dirs, files in os.walk(the_path) :
        for fil in files :
            if re.search(key, fil) :
                path_size += os.path.getsize(the_path + "/" + fil)
        return path_size





## Determines between various truncated codestream, which is better, in terms of bit-rate and rmse.
#  @param FIRST_picture_ofGOP Number of the first image of the GOP.
#  @param iGOP GOP number of the current iteration.
#  @param pictures Total number of images to process. It may correspond to the images of a GOP, or all images in the sequence.
#  @param kbps_antes Kbps of a truncated codestream. These Kbps are taken as reference for future comparisons.
#  @param rmse1D_antes Distortion of a truncated codestream. This distortion is taken as reference for future comparisons.
#  @param radian_candidato Index linking the pair R / D (rate-distortion). The higher the index, the higher value of the codestream.
#  @param kbps_candidato Codestream kbps from the best known so far.
#  @param rmse1D_candidato Distorsion from the codestream best known so far.
#  @param _CANDIDATO List the number of layers for each sub-band, best known so far codestream.
#  @param _CANDIDATO_REDUCES List of reductions in the spatial resolution for each subband (for the best codestream). Its default value is 0. Not usually used because, as scalability gives better results.
#  @param _CANDIDATO_REDUCES_normalized List of reductions in the spatial resolution for each subband. In which, the reduction values are tested for changes in spatial resolution, do not lead to problems with block sizes, etc. Its default value is 0. Not usually used because, as scalability gives better results.
#  @param emptyLayer Indicates whether the codestream has empty layers.
#  @param CANDIDATO_KBPS Codestream kbps Known from the best so far; detailed for each subband and motion field.
#  @param _COMBINATION List the number of layers of each subband from a codestream.
#  @param _COMBINATION_REDUCES List of reductions in the spatial resolution for each subband (for a codestream evaluation).
#  @param snr_fileA Original sequence or part of it. This is not the video stream but a link to it.
#  @param snr_fileB Reconstruction of a codestream or part of it. This is not the video stream but a link to it.
#  @return List the number of layers for each sub-band, best known so far codestream, called candidate.
def lba (FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB) : # looking the best angle

    # Displays information about the execution:
    # raw_input("_COMBINATION en lba: " + str(_COMBINATION)) # !
    # raw_input("_REDUCES en lba: " + str(_REDUCES)) # !
    # raw_input("ANTES TRANSCODE") # !
    # check_call("echo lba:" + str(FIRST_picture_ofGOP) + " " + str(pictures), shell=True) # !
    # raw_input("")


    # Normalize reduces.
    #-------------------
    _COMBINATION_REDUCES_normalized = _COMBINATION_REDUCES[:]
    for i in range (0, len(_COMBINATION_REDUCES)) :
        if _COMBINATION_REDUCES[i] > _REDUCES_normalizer[i] :
            _COMBINATION_REDUCES_normalized[i] = _REDUCES_normalizer[i]

    # Displays information about the execution:
    # check_call("echo " + str(_COMBINATION_REDUCES_normalized),shell=True) # !
    # raw_input("")



    # New values, resolution and block size, after applying the reduction in spatial resolution.
    #-------------------------------------------------------------------------------------------
    _PIXELS_IN_X = []
    _PIXELS_IN_Y = []
    _BLOCK_SIZES = []

    # Scaling the resolution (REDUCES) affects: PIXELS_IN_XY and BLOCK_SIZES.
    for i in range (0, TRLs) : # T
        _PIXELS_IN_X.append(pixels_in_x/pow(2,_COMBINATION_REDUCES_normalized[i])) # RES_X_transcode=`echo "$RES_X/(2^$discard_SRLs_Tex)" | bc`
        _PIXELS_IN_Y.append(pixels_in_y/pow(2,_COMBINATION_REDUCES_normalized[i]))
        if i > 0 :
            _BLOCK_SIZES.append(block_size/pow(2,_COMBINATION_REDUCES_normalized[i]))
    for i in range (TRLs, N_subbands) : # M
        _BLOCK_SIZES[i-TRLs] = _BLOCK_SIZES[i-TRLs]*pow(2,_COMBINATION_REDUCES_normalized[i]) # block_size_transcode=`echo "$block_size/(2^$discard_SRLs_Tex)" | bc`


 
    # Severability. Verify new values: resolution and block size are acceptable by the codec.
    #----------------------------------------------------------------------------------------
    for i in range (1, TRLs) :
        if 0 != _PIXELS_IN_X[i] % _BLOCK_SIZES[i-1] or 0 != _PIXELS_IN_Y[i] % _BLOCK_SIZES[i-1] :
            check_call("echo La resolucion \(" + str(_PIXELS_IN_X[i]) + "x" + str(_PIXELS_IN_Y[i]) + "\) is not divisible by the size of macroblock \(" + str(_BLOCK_SIZES[i-1]) + "\)"
                       , shell=True)
            exit (0)

    # Displays information about the execution:
    # check_call("echo \"\n--block_size="  + ','.join(map(str, _BLOCK_SIZES))
    #           + "\n--pixels_in_x="       + ','.join(map(str, _PIXELS_IN_X))
    #           + "\n--pixels_in_y="       + ','.join(map(str, _PIXELS_IN_Y))
    #           + "\n--subpixel_accuracy=" + ','.join(map(str, _COMBINATION_REDUCES_normalized[:TRLs])) + "\""
    #           ,shell=True)
    # raw_input("")



    # EXTRACT. Extract the folder '/extract'.
    #----------------------------------------
    transcode (N_subbands, FIRST_picture_ofGOP, pictures, _COMBINATION, _COMBINATION_REDUCES_normalized)



    # Copy to folder '/extract', the auxiliary files, called (frame_types_).
    #-----------------------------------------------------------------------
    pictures = 1 * GOP_size + 1
    subband = 1
    while subband < TRLs :
        pictures = pictures / 2 # !
        p = sub.Popen("dd"
                      + " if="    + str(path_base)    + "/frame_types_" + str(subband)
                      + " of="    + str(path_extract) + "/frame_types_" + str(subband)
                      + " skip="  + str(iGOP-1)
                      + " bs="    + str(pictures)
                      + " count=" + str(GOPs_to_expand)
                      , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        out, err = p.communicate()
        subband += 1



    # Shipping.
    #----------
    p = sub.Popen("rm -rf " + str(path_tmp) + "; mkdir " + str(path_tmp)
                  + "; echo \"ENVIO: \"; ls -l " + str(path_extract) # echo
                  + "; cp " + str(path_extract) + "/* " + str(path_tmp)
                  , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
    out, err = p.communicate()
    #errcode = p.returncode




    # info.py (Kbps).
    #----------------
    os.chdir(path_extract)

    instancia_info_j2k                              = info_j2k.info_j2k(GOPs_to_expand, TRLs, FPS)     # Only for j2k codec.
    kbps_M_average, kbps_T_average, kbps_TM_average = instancia_info_j2k.kbps_average()
    kbps_M,         kbps_T,         kbps_TM         = instancia_info_j2k.kbps()                        # kbps_TM[0] = kbps del GOP0 (primera imagen L).
                                                                                                       # kbps_TM[1] = kbps del GOP1.
                                                                                                       # kbps_TM[2] = kbps del GOP2. (and so on)
    TO_KBPS  = 8.0 / duration / 1000
    kbps_ALL = get_size(path_extract, "") * TO_KBPS



    # EXPAND.
    #--------
    os.chdir(path_tmp)

    check_call("mcj2k expand"  # mcj2k expand --GOPs=1 --TRLs=5 --SRLs=5 --block_size=16,16,16,16 --search_range=4 --pixels_in_x=352,352,352,352,352 --pixels_in_y=288,288,288,288,288 --subpixel_accuracy=0,0,0,0,0
               + " --GOPs="              + str(GOPs_to_expand)
               + " --TRLs="              + str(TRLs)
               + " --SRLs="              + str(SRLs)
               + " --update_factor="     + str(update_factor)
               + " --block_size="        + ','.join(map(str, _BLOCK_SIZES))
               + " --block_size_min="    + str(block_size_min)
               + " --search_range="      + str(search_range)
    #          + " --rates="             + str(','.join(map(str, _RATES))) # In construction.
               + " --pixels_in_x="       + ','.join(map(str, _PIXELS_IN_X))
               + " --pixels_in_y="       + ','.join(map(str, _PIXELS_IN_Y))
               + " --subpixel_accuracy=" + ','.join(map(str, _COMBINATION_REDUCES_normalized[:TRLs]))
               , shell=True)



    # info (RMSE).
    #-------------

    # Video completo
    # --file_A=low_0 --file_B=../low_0(iGOP)

    # Sub Independientes
    # --file_A=high_4 --file_B=../high_4
    # --file_A=high_3 --file_B=../high_3
    # --file_A=high_2 --file_B=../high_2
    # --file_A=high_1 --file_B=../high_1
    # --file_A=low_0 --file_B=../low_0(iGOP)

    # For subband 2.5
    # --file_A=low_0 --file_B=../low_4
    # --file_A=low_0 --file_B=../low_3
    # --file_A=low_0 --file_B=../low_2
    # --file_A=low_0 --file_B=../low_1
    # --file_A=low_0 --file_B=../low_0_original

    # Log information about the execution.
    check_call("echo \"" + "snr fileA=" + str(snr_fileA) + " fileB=" + str(snr_fileB) + " " + str(_COMBINATION) + "\" >> " + str(path_base) + "/info_snrFiles", shell=True)
    # RMSE for each frame. Bytes of each frame = 352�288�1,5 = 152064 (CIF).
    check_call("echo \"" + "snr fileA=" + str(snr_fileA) + " fileB=" + str(snr_fileB) + " --block_size=" + str(int(pixels_in_x * pixels_in_y * 1.5)) + " " + str(_COMBINATION) + "\" >> " + str(path_base) + "/info_snrFrames_GOP" + str(iGOP), shell=True)
    check_call("snr --file_A=" + str(snr_fileA) + " --file_B=" + str(snr_fileB) + " --block_size=" + str(int(pixels_in_x * pixels_in_y * 1.5)) + " 2>> " + str(path_base) + "/info_snrFrames_GOP" + str(iGOP), shell=True)
    # RMSE average for all frames.
    p = sub.Popen("snr --file_A=" + str(snr_fileA) + " --file_B=" + str(snr_fileB) + " 2> /dev/null | grep RMSE | cut -f 3", shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
    out, err = p.communicate()
    #errcode = p.returncode
    if out == "" : #if err in locals() :
        check_call("echo SNR sin salida.", shell=True)
        exit (0)

    rmse1D = float(out)



    # KBPS y RMSE.
    #-------------
    KBPS_DATA   = ""
    KBPS_DATA  += "  M "          + str(kbps_M_average)      # array dimension = TRLs
    KBPS_DATA  += "\toutL "       + str(kbps_T[0])           # array dimension = 1
    KBPS_DATA  += "\tT "          + str(kbps_T[-1:])         # array dimension = TRLs
    KBPS_DATA  += "\tTM "         + str(kbps_TM)             # array dimension = GOPs
    KBPS_DATA  += "\tTM_average " + str(kbps_TM_average)     # array dimension = 1
    KBPS_DATA  += "\tRMSE "       + str(rmse1D) + "\t:: "    # array dimension = 1
    KBPS_DATA   = KBPS_DATA.replace("[", "")
    KBPS_DATA   = KBPS_DATA.replace("]", "")
    KBPS_DATA   = KBPS_DATA.replace(",", " ")



    # Angles.
    #--------
    os.chdir(path_base)

    # RADIAN.
    radian = 0 # fuzzy Python

    # JIGGER.
    if _COMBINATION == _CEROS :
        rmse1D_antes = rmse1D
        kbps_antes   = kbps_TM[1]                                                              # kbps @@@
        _CANDIDATO_REDUCES_normalized = _COMBINATION_REDUCES_normalized[:]

    else :
        if rmse1D_antes > rmse1D :    # >
            emptyLayer = 0

            if kbps_TM[1] == kbps_antes :
                # Improve the quality of the reconstruction without
                # increasing kbps, seems impossible but can occur in
                # this research environment.

                # A codestream is formed by a set of GOPS, besides the
                # GOP0, which is formed by an image of the L subband.

                # The GOP0 taken into account in the info.py function
                # for the complete codestream.

                # Sorting algorithms work at the level of a single
                # GOP, however, all codestream needs your GOP0, so in
                # this situation, the GOP0 corresponds to the last
                # image of the previous GOP, which was already
                # measured.

                # It may be the case in a sorting algorithm,
                # evaluating quality pillowtop, the codestream: GOP0
                # grow in, but does not grow in the GOP1, so both have
                # the same codestream kbps, since only look at the
                # GOP1, but have different rmse.

                radian = math.atan ( (rmse1D_antes - rmse1D) / 0.001 ) # A little value.
            else :
                radian = math.atan ( (rmse1D_antes - rmse1D) / (kbps_TM[1] - kbps_antes) )     # kbps @@@

            if radian > radian_candidato :
                kbps_candidato                = kbps_TM[:]                                     # kbps @@@
                rmse1D_candidato              = rmse1D
                radian_candidato              = radian
                _CANDIDATO                    = _COMBINATION[:]
                _CANDIDATO_REDUCES            = _COMBINATION_REDUCES[:]
                _CANDIDATO_REDUCES_normalized = _COMBINATION_REDUCES_normalized[:]
                CANDIDATO_KBPS                = KBPS_DATA

        else :                        # <=
            emptyLayer += 1
            check_call("echo \"" + str(_COMBINATION) + " * " + str(_COMBINATION_REDUCES_normalized) + KBPS_DATA      + "No rectangulo \" >> " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle", shell=True)
            return kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS

    if GOPs_to_expand != GOPs :
        check_call("echo \"" + str(_COMBINATION) + " * " + str(_COMBINATION_REDUCES_normalized) + KBPS_DATA + str("%.9f" % radian) + "\" >> " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle", shell=True)
    else :
        check_call("echo \"" + str(_COMBINATION) + " * " + str(_COMBINATION_REDUCES_normalized) + KBPS_DATA + str("%.9f" % radian) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs"              + "_detalle", shell=True)

    check_call("echo \"Y :: " + str(_RATES_Y)  + "\" >> " + str(INFO) + "_rates", shell=True)
    check_call("echo \"U :: " + str(_RATES_U)  + "\" >> " + str(INFO) + "_rates", shell=True)
    check_call("echo \"V :: " + str(_RATES_V)  + "\" >> " + str(INFO) + "_rates ; echo >> " + str(INFO) + "_rates", shell=True)
    return kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS






# A) For Subbands xTRLs, 'lowx' and '../low_x' (MCJ2K)
# All L4 layer to layer, M4, all H3 layer to layer, M3, all H2 layer to layer, M2, ...
# Ie: 1�capa_L4, 2�capa_L4, 3�capa_L4, ... M4, 1capa_H4, 2capa_H4, 3capa_H4, ... , M3,
# RMSE: with lowx (only tested subbands).
#--------------------------------------------------------

## Sorting algorithm: Progressive Transmission by Subbands (PTS): This
## BRC strategy consists in requesting the code-stream in the order
## L^T, M^T, H^T, M^(T-1), H^(T-1), ..., M^1, H^1, which
## correspond to a progressive increment of the temporal resolution of
## the reconstruction. Calculating the distortion is performed
## regarding a subset of subbands. The truncated codestream consists
## of layers of certain subbands; distortion is performed with respect
## to the same subset of complete subbands.
#
#  @param _CAPAS_COMPLETAS Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
def MCJ2K_for_Subbands__rmse_lowx (_CAPAS_COMPLETAS) :

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    # Variables
    _ENVIO_VACIO  = ([0] * len(_CAPAS_COMPLETAS))
    _ENVIOS       = []
    _EVALUACIONES = []
    _SUB_EVALUADA = []

    FIRST_picture_ofGOP = 0
    pictures            = GOPs * GOP_size + 1
    GOPs_to_expand      = GOPs
    iGOP                = 1
    snr_fileA           = None
    snr_fileB           = None # Here it does not exist "../low_0_original" or "../low_0+iGOP"

    # 1. DEFINE ASSESSMENTS. Initialization _ENVIOS (variable describing shipments)
    _ENVIOS.append(_ENVIO_VACIO[:])                              # _SHIPPING
    _SUB_EVALUADA.append(_ENVIO_VACIO[:])                        # _SUB_EVALUATED    (Indicates the subband evaluated).
    for uu in range (0, TRLs) :
        for u in range (1, _CAPAS_COMPLETAS[uu]+1) :
            _ENVIOS[len(_ENVIOS)-1][uu] = u                      # _SHIPPING       # Add texture layers.
            _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu] = 1          # _SUB_EVALUATED  # Indicates the texture layer.
            if u < _CAPAS_COMPLETAS[uu] :                        
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])       # _SHIPPING
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])            # _SUB_EVALUATED
            if u == _CAPAS_COMPLETAS[uu] and uu < TRLs-1 :       
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])       # _SHIPPING
                _ENVIOS[len(_ENVIOS)-1][uu+TRLs] = 1             # _SHIPPING       # Add vectors.
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])       # _SHIPPING
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])            # _SUB_EVALUATED
                _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu+TRLs] = 1 # _SUB_EVALUATED  # Indicates the vector.
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])            # _SUB_EVALUATED

    # Displays information about the execution:
    # print '\n'.join(map(str, _ENVIOS))
    # print '\n'.join(map(str, _SUB_EVALUADA))

    for u in range (0, len(_SUB_EVALUADA)) :

        # Upgrade comparing the SNR.
        _sub_sent = [[i for i, x in enumerate(_SUB_EVALUADA[u]) if x == e] for e in [1]]
        if _sub_sent[0][0] >= TRLs :
            _sub_sent[0][0] = _sub_sent[0][0] - (TRLs-1)
        snr_fileA = "low_" + str(TRLs-1-_sub_sent[0][0]) # rmse of subband_x and low_x.
        snr_fileB = "../" + snr_fileA
        #print str(_sub_sent[0][0]) + " " + str(snr_fileB) # !!

        # CHECK THE SHIPPING OPTIMIZED.
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # PRINT a file # info.py  is applied to the entire video, namely, the average is already done.
        check_call("echo \"" + str(kbps_TM_average) + "\t " + str(rmse1D) + "\t " + str(_sub_sent[0][0]) + "\t" + str(_COMBINATION) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages_gnuplot", shell=True)

    return 0







# 1) Progressive Transmission by Subbands (PTS)
# For Subbands.
# All L4 layer to layer, M4, all H3 layer to layer, M3, all H2 layer to layer, M2, ...
# Ie: 1�capa_L4, 2�capa_L4, 3�capa_L4, ... M4, 1capa_H4, 2capa_H4, 3capa_H4, ... , M3,
# RMSE: 'lowx' and '../low_0' (full video)
#--------------------------------------------------------------------

## Sorting algorithm: Progressive Transmission by Subbands (PTS): This
## BRC strategy consists in requesting the code-stream in the order
## L^T, M^T, H^T, M^(T-1), H^(T-1), ..., M^1 , H^1, which
## correspond to a progressive increment of the temporal resolution of
## the reconstruction. Calculating the distortion is performed always
## with the original video.
#
#  @param _CAPAS_COMPLETAS Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
def for_Subbands__rmse_low0 (_CAPAS_COMPLETAS) :

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    # Variables
    _ENVIO_VACIO  = ([0] * len(_CAPAS_COMPLETAS))
    _ENVIOS       = []
    _EVALUACIONES = []
    _SUB_EVALUADA = []

    FIRST_picture_ofGOP = 0
    pictures            = GOPs * GOP_size + 1
    GOPs_to_expand      = GOPs
    iGOP                = 1
    snr_fileA           = "low_0"
    snr_fileB           = "../low_0" # Here it does not exist "../low_0_original" or "../low_0+iGOP"

    # 1. DEFINE ASSESSMENTS. Initialization _ENVIOS (variable describing shipments)
    _ENVIOS.append(_ENVIO_VACIO[:])                              # _SHIPPING
    _SUB_EVALUADA.append(_ENVIO_VACIO[:])                        # _SUB_EVALUATED
    for uu in range (0, TRLs) :
        for u in range (1, _CAPAS_COMPLETAS[uu]+1) :
            _ENVIOS[len(_ENVIOS)-1][uu] = u                      # _SHIPPING       # Add texture layers.
            _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu] = 1          # _SUB_EVALUATED  # Indicates the texture layer.
            if u < _CAPAS_COMPLETAS[uu] :                        
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])       # _SHIPPING
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])            # _SUB_EVALUATED
            if u == _CAPAS_COMPLETAS[uu] and uu < TRLs-1 :       
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])       # _SHIPPING
                _ENVIOS[len(_ENVIOS)-1][uu+TRLs] = 1             # _SHIPPING       # Add vectors.
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])       # _SHIPPING
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])            # _SUB_EVALUATED
                _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu+TRLs] = 1 # _SUB_EVALUATED  # Indicates the vector.
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])            # _SUB_EVALUATED

    # Displays information about the execution:
    # print '\n'.join(map(str, _SHIPPING))
    # print '\n'.join(map(str, _SUB_EVALUATED))


    for u in range (0, len(_SUB_EVALUADA)) :

        # INDICATES subband updated and can be displayed on a graph with the added layer at all times.
        _sub_sent = [[i for i, x in enumerate(_SUB_EVALUADA[u]) if x == e] for e in [1]]

        # CHECK THE SHIPPING OPTIMIZED.
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # PRINT a file # info.py  is applied to the entire video, namely, the average is already done.
        check_call("echo \"" + str(kbps_TM_average) + "\t " + str(rmse1D) + "\t " + str(_sub_sent[0][0]) + "\t" + str(_COMBINATION) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages_gnuplot", shell=True)

    return 0




# 2) Progressive Transmission by Layers (PTL)
# For Layers
# Niveles de capas, capa a capa: todas las primeras capas de cada subbanda, todos los vectores, las segundas capas, las terceras ...
# 1capa_L4, M4, 1capa_H4, M3, 1capa_H3, M2, 1capa_H2, M1, 1capa_H1, 2capa_L4, 2capa_H4, 2capa_H3, 2capa_H2, 2capa_H1, 3capa_L4, 3capa_H4, ....
#-----------------------------------------------------------

## Sorting algorithm: Progressive Transmission by Layers (PTL): This
## strategy is similar to PTR, but the quality layers of the subbands
## are interleaved, starting at the layer 1. Therefore, at any
## instant of the transmission, the (or almost the) same the number of
## quality layers of each subband has been transmitted.
#
#  @param _CAPAS_COMPLETAS Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
def for_Layers (_CAPAS_COMPLETAS) :

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    # Variables
    _ENVIO_VACIO  = ([0] * len(_CAPAS_COMPLETAS))
    _ENVIOS       = []
    _EVALUACIONES = []
    _SUB_EVALUADA = []

    FIRST_picture_ofGOP = 0
    pictures            = GOPs * GOP_size + 1
    GOPs_to_expand      = GOPs
    iGOP                = 1
    snr_fileA           = "low_0"
    snr_fileB           = "../low_0" # Here it does not exist "../low_0_original" or "../low_0+iGOP"

    # 1. DEFINE ASSESSMENTS. Initialization _ENVIOS (variable describing shipments)
    _ENVIOS.append(_ENVIO_VACIO[:])                                           # _SHIPPING
    _SUB_EVALUADA.append(_ENVIO_VACIO[:])                                     # _SUB_EVALUATED
    for u in range (1, Ncapas_T+1) :
        for uu in range (0, TRLs) :
            _ENVIOS[len(_ENVIOS)-1][uu] = u                                   # _SHIPPING
            _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu] = 1                       # _SUB_EVALUATED
            if _ENVIOS[len(_ENVIOS)-1][TRLs-1] < Ncapas_T :
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])                    # _SHIPPING
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])                         # _SUB_EVALUATED
            if uu < TRLs-1 and 0 == _ENVIOS[len(_ENVIOS)-1][uu+TRLs] :
                _ENVIOS[len(_ENVIOS)-1][uu+TRLs] = 1                          # _SHIPPING
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])                    # _SHIPPING
                _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu+TRLs] = 1              # _SUB_EVALUATED
                _SUB_EVALUADA.append(_ENVIO_VACIO[:])                         # _SUB_EVALUATED

    # Displays information about the execution:
    # print '\n'.join(map(str, _ENVIOS))
    # print '\n'.join(map(str, _SUB_EVALUADA))

    for u in range (0, len(_SUB_EVALUADA)) :

        # INDICATES subband updated and can be displayed on a graph with the added layer at all times.
        _sub_sent = [[i for i, x in enumerate(_SUB_EVALUADA[u]) if x == e] for e in [1]]

        # CHECK THE SHIPPING OPTIMIZED.
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # PRINT a file # info.py  is applied to the entire video, namely, the average is already done.
        check_call("echo \"" + str(kbps_TM_average) + "\t " + str(rmse1D) + "\t " + str(_sub_sent[0][0]) + "\t" + str(_COMBINATION) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages_gnuplot", shell=True)

    return 0





# 3) Attenuation-modulated PTL (AmPTL)
# Layers ordered by gains
# Send layers of each subband sorted according GAINS.
#----------------------------------------------------

## Sorting algorithm: Attenuation-modulated PTL (AmPTL): This
## algorithm is similar to PTQ, althought the energy attenuation
## values of Table I have been used to decide the number of quality
## layers to transmit of each temporal subband, each time the next
## temporal subband is transmitted.
#
#  @param _CAPAS_COMPLETAS Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
def Gains_Layers (_CAPAS_COMPLETAS) :

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    # Variables
    _ENVIO_VACIO  = ([0] * len(_CAPAS_COMPLETAS))
    _ENVIOS       = []
    _EVALUACIONES = []
    _SUB_EVALUADA = []

    FIRST_picture_ofGOP = 0
    pictures            = GOPs * GOP_size + 1
    GOPs_to_expand      = GOPs
    iGOP                = 1
    snr_fileA           = "low_0"
    snr_fileB           = "../low_0" # Here it does not exist "../low_0_original" or "../low_0+iGOP"

    # 1. DEFINE ASSESSMENTS. Initialization _ENVIOS (variable describing shipments)
    # GAINS 5TRLs = [1.0877939347, 2.1250255455, 3.8884779989, 5.8022196044] = [1, 2, 4, 6]
    #            [1,2,4,6]
    #             | | | |
    _ENVIOS = [[0,0,0,0,0,0,0,0,0],
               [1,0,0,0,0,0,0,0,0],
               [1,0,0,0,0,1,0,0,0],
               [1,1,0,0,0,1,0,0,0],
               [2,1,0,0,0,1,0,0,0],
               [2,2,0,0,0,1,0,0,0],
               [2,2,0,0,0,1,1,0,0],
               [2,2,1,0,0,1,1,0,0],
               [3,2,1,0,0,1,1,0,0],
               [3,3,1,0,0,1,1,0,0],
               [4,3,1,0,0,1,1,0,0],
               [4,4,1,0,0,1,1,0,0],
               [4,4,2,0,0,1,1,0,0],
               [4,4,2,0,0,1,1,1,0],
               [4,4,2,1,0,1,1,1,0],
               [5,4,2,1,0,1,1,1,0],
               [5,5,2,1,0,1,1,1,0],
               [6,5,2,1,0,1,1,1,0],
               [6,6,2,1,0,1,1,1,0],
               [6,6,3,1,0,1,1,1,0],
               [6,6,3,1,0,1,1,1,1],
               [6,6,3,1,1,1,1,1,1],
               [7,6,3,1,1,1,1,1,1],
               [7,7,3,1,1,1,1,1,1],
               [8,7,3,1,1,1,1,1,1],
               [8,8,3,1,1,1,1,1,1],
               [8,8,4,1,1,1,1,1,1],
               [8,8,4,2,1,1,1,1,1],
               [9,8,4,2,1,1,1,1,1],
               [9,9,4,2,1,1,1,1,1],
               [10,9,4,2,1,1,1,1,1],
               [10,10,4,2,1,1,1,1,1],
               [10,10,5,2,1,1,1,1,1],
               [11,10,5,2,1,1,1,1,1],
               [11,11,5,2,1,1,1,1,1],
               [12,11,5,2,1,1,1,1,1],
               [12,12,5,2,1,1,1,1,1],
               [12,12,6,2,1,1,1,1,1],
               [12,12,6,3,1,1,1,1,1],
               [12,12,6,3,2,1,1,1,1],
               [13,12,6,3,2,1,1,1,1],
               [13,13,6,3,2,1,1,1,1],
               [13,13,6,3,2,1,1,1,1],
               [14,13,6,3,2,1,1,1,1],
               [14,14,6,3,2,1,1,1,1],
               [14,14,7,3,2,1,1,1,1],
               [15,14,7,3,2,1,1,1,1],
               [15,15,7,3,2,1,1,1,1],
               [16,15,7,3,2,1,1,1,1],
               [16,16,7,3,2,1,1,1,1],
               [16,16,8,3,2,1,1,1,1], # GAINS 5TRLs = [1.953518472, 3.574645781, 5.333932668] = [2, 4, 5]
               [16,16,8,4,2,1,1,1,1], # GAINS 5TRLs = [1.829850003, 2.730423461] = [2, 3]
               [16,16,9,4,2,1,1,1,1],
               [16,16,9,4,3,1,1,1,1],
               [16,16,10,4,3,1,1,1,1],
               [16,16,10,5,3,1,1,1,1],
               [16,16,11,5,3,1,1,1,1],
               [16,16,12,5,3,1,1,1,1],
               [16,16,12,6,3,1,1,1,1],
               [16,16,12,6,4,1,1,1,1],
               [16,16,13,6,4,1,1,1,1],
               [16,16,14,6,4,1,1,1,1],
               [16,16,14,7,4,1,1,1,1],
               [16,16,15,7,4,1,1,1,1],
               [16,16,15,7,5,1,1,1,1],
               [16,16,16,7,5,1,1,1,1],
               [16,16,16,8,5,1,1,1,1],
               [16,16,16,8,6,1,1,1,1], # GAINS 5TRLs = [1.492156984] = [1]
               [16,16,16,8,7,1,1,1,1],
               [16,16,16,8,8,1,1,1,1],
               [16,16,16,9,8,1,1,1,1],
               [16,16,16,9,9,1,1,1,1],
               [16,16,16,10,9,1,1,1,1],
               [16,16,16,10,10,1,1,1,1],
               [16,16,16,11,10,1,1,1,1],
               [16,16,16,11,11,1,1,1,1],
               [16,16,16,12,11,1,1,1,1],
               [16,16,16,12,12,1,1,1,1],
               [16,16,16,13,12,1,1,1,1],
               [16,16,16,13,13,1,1,1,1],
               [16,16,16,14,13,1,1,1,1],
               [16,16,16,14,14,1,1,1,1],
               [16,16,16,15,14,1,1,1,1],
               [16,16,16,15,15,1,1,1,1],
               [16,16,16,16,15,1,1,1,1],
               [16,16,16,16,16,1,1,1,1]]


    # CHECK THE SHIPPING OPTIMIZED.
    for u in range (0, len(_ENVIOS)) :
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # PRINT a file # info.py  is applied to the entire video, namely, the average is already done.
        check_call("echo \"" + str(kbps_TM_average) + "\t " + str(rmse1D) + "\t " + str(_COMBINATION) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages_gnuplot", shell=True)

    return 0



## Fill lists as they get to know the values kbps and rmse of each GOP
## in ordination algorithms that manage GOP to GOP.
#
#  @param iGOP GOP number of the current iteration.
#  @param AVERAGES Empty list of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @param RMSEs Empty list of distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @param kbps_TM Kbps of the current codestream truncated in the current GOP.
#  @param rmse1D Rmse of the current codestream truncated in the current GOP.
#  @return Three lists of values as a result is obtained:
#  - Ordered list of layers from codestream.
#  - Mean kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
#  - Distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
def save_AVERAGES (iGOP, AVERAGES, RMSEs, kbps_TM, rmse1D) :

    if iGOP == 1 and AVERAGES[0] == [] :
        AVERAGES[0].append(kbps_TM[0]) # El GOP0
        RMSEs   [0].append(0)

    AVERAGES[iGOP].append(kbps_TM[1])  # El GOPn
    RMSEs   [iGOP].append(rmse1D)

    return AVERAGES, RMSEs





# Unweighted average of GOPs 1 to N.
#-----------------------------------

## Makes the unweighted average of a sequence of GOPs. This task is
## carried out info.py, under normal circumstances, however, when an
## algorithm, the which runs GOP to GOP, info.py never received the
## full sequence, and therefore can not perform this task.
#
#  @param AVERAGES List of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @param RMSEs List of distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @return 
#  - List of kbps averages with the unweighted average of a sequence of GOPs.
#  - List of rmse averages with the unweighted average of a sequence of GOPs.
def averages_1toN (AVERAGES, RMSEs) :

    # Input data sample:
    # GOPs     = 2
    # AVERAGES = [[1], [2,3,4], [5,6,7]]                                                    # kbps
    # RMSEs    = [[0], [2,3,4], [5,6,7]]                                                    # rmse

    AVERAGES.append([])                            # Unweighted average of the GOPs 1 to N in kbps.
    RMSEs.append   ([])                            # Unweighted average of the GOPs 1 to N in rmse.
    for kbps in range (0, len(AVERAGES[1])) :
        AVERAGES[len(AVERAGES)-1].append(0)                                                 # kbps
        RMSEs   [len(RMSEs   )-1].append(0)                                                 # rmse
        for gop in range (1, len(AVERAGES)-1) :
            try :
                AVERAGES[len(AVERAGES)-1][kbps] += AVERAGES[gop][kbps]                      # kbps
                RMSEs   [len(RMSEs   )-1][kbps] += RMSEs   [gop][kbps]                      # rmse
            except IndexError :
                AVERAGES[len(AVERAGES)-1].pop(kbps)                                         # kbps
                RMSEs   [len(RMSEs   )-1].pop(kbps)                                         # rmse
                return AVERAGES, RMSEs
        AVERAGES[len(AVERAGES)-1][kbps] = (1.0 * AVERAGES[len(AVERAGES)-1][kbps]) / GOPs    # kbps
        RMSEs   [len(RMSEs   )-1][kbps] = (1.0 * RMSEs   [len(RMSEs   )-1][kbps]) / GOPs    # rmse
    return AVERAGES, RMSEs





# Weighted average of GOPs 0 y N.
#--------------------------------

## Makes the weighted average of a sequence of GOPs. This task is
## carried out info.py, under normal circumstances, however, when an
## algorithm, the which runs GOP to GOP, info.py never received the
## full sequence, and therefore can not perform this task.
#
#  @param AVERAGES List of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @return List of kbps averages with the weighted average of a sequence of GOPs.
def averages_0yN (AVERAGES) :

    # Input data sample:
    # pictures = 17
    # AVERAGES=[[1], [2, 3, 4], [5, 6], [3.5, 4.5]]

    pictures    = GOPs * GOP_size + 1 # The full sequence (All images of all gops).
    ponderacion = (pictures - 1.0) / pictures
    AVERAGES.append([])
    for kbps in range (0, len(AVERAGES[len(AVERAGES)-2])) :
        AVERAGES[len(AVERAGES)-1].append(0)
        AVERAGES[len(AVERAGES)-1][kbps] = (AVERAGES[0][0] * (1 - ponderacion)) + (AVERAGES[len(AVERAGES)-2][kbps] * ponderacion)
    return AVERAGES





# AVERAGES de GOPs a fichero (gnuplot).
#--------------------------------------

## Write to a file stockings kbps and distortions. It is useful to
## show the final results, using a third tool, such as gnuplot.
#
#  @param AVERAGES List of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @param RMSEs List of distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
def averages_file (AVERAGES, RMSEs) :

    # Input data sample:
    # from subprocess   import check_call
    # INFO     = "info"
    # AVERAGES = [[1], [2, 3, 4], [5, 6, 7], [3.5, 4.5, 5.5], [3.352941176470588, 4.294117647058823, 5.235294117647059]]
    # RMSEs    = [[0], [2, 3, 4], [5, 6, 7], [3.3, 4.2, 5.2]]

    # PRINT: Raw data.
    check_call("echo \"\nAVERAGES\n" + str(AVERAGES) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages", shell=True)
    check_call("echo \"\nRMSEs   \n" + str(RMSEs)    + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages", shell=True)
    # PRINT: Formatted for gnuplot.
    for u in range (0, len(AVERAGES[len(AVERAGES)-1])) :
        try :
            average = str(AVERAGES[len(AVERAGES)-1][u])
            rmse    = str(RMSEs   [len(RMSEs   )-1][u])
            check_call("echo \"" + average + "\t " + rmse + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages_gnuplot", shell=True)
        except IndexError :
            break

    # After filing the middle, initializes variables. (No need ..)
    AVERAGES         = [[] for x in xrange (GOPs + 1)]
    RMSEs            = [[] for x in xrange (GOPs + 1)]
    return AVERAGES, RMSEs






# 4) Full Search.
#----------------

## Sorting algorithm: Full Search R/D optimization (FS-opt): This
## technique is based on the idea that the optimal order of subbands
## and quality layers of a compressed video can be determined by
## checking all the feasible combinations of quality layers of
## subbands and sorting them by their contribution to the
## minimization of the distortion the reconstructed GOP.
#
#  @param iGOP GOP number of the current iteration.
#  @param FIRST_picture_ofGOP Number of the first image of the GOP.
#  @param pictures Total number of images to process. It may correspond to the images of a GOP, or all images in the sequence.
#  @param _CAPAS_COMPLETAS Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
#  @param AVERAGES Empty list of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @param RMSEs Empty list of distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @return Three lists of values as a result is obtained:
#  - Ordered list of layers from codestream.
#  - Mean kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
#  - Distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
def BRC_BruteForce (iGOP, FIRST_picture_ofGOP, pictures, _CAPAS_COMPLETAS, AVERAGES, RMSEs) : #, _layerAdded) :

    # Variables of the LBA function (python calls declare).
    snr_fileA        = "low_0"
    snr_fileB        = "../low_0" + str(iGOP) # Each GOP is independent of the others.
    KBPS_DATA        = ""
    CANDIDATO_KBPS   = ""

    kbps_antes       = 0
    kbps_candidato   = [0, 0]
    kbps_TM          = [0, 0]
    kbps_TM_average  = 0

    rmse1D           = 0
    rmse1D_antes     = MAX_VALUE
    rmse1D_candidato = 0

    radian_candidato = -MAX_VALUE
    radian           = 0

    emptyLayer       = 0

    _CEROS           = [0] * N_subbands
    _CAPAS           = [0] * N_subbands
    _COMBINATION     = [0] * N_subbands
    _CANDIDATO       = [0] * N_subbands
    #_CAPAS_VACIAS = # for future optimization.

    # This form initialize a list works for one list but not on a list of lists.
    _COMBINATION_REDUCES            = ([Nclevels_T+1] * TRLs) + ([Nclevels_M+1] * (TRLs-1)) # +1: Because the BRC first modified and then evaluated.
    _CANDIDATO_REDUCES              = _COMBINATION_REDUCES[:]
    _REDUCES_normalizer             = ([Nclevels_T] * TRLs) + ([Nclevels_M] * (TRLs-1))
    _CANDIDATO_REDUCES_normalized   = []
    _COMBINATION_REDUCES_normalized = []

    # Initialize _REDUCES
    _REDUCES = map(int, discard_SRLs.split(','))

    error = False

    if len(_REDUCES) != N_subbands :
        check_call("echo discard_SRLs: its length must be " + str(N_subbands) + " with TRL=" + str(TRLs) + ".", shell=True) # Types
        error = True

    if error == True :
        _REDUCES = [0] * N_subbands #_REDUCES = ([Nclevels_T] * TRLs) + ([Nclevels_M] * (TRLs-1))
        check_call("echo discard_SRLs default = " + str(_REDUCES) + "   Press ENTER to continue...", shell=True) # Types

    if BRC == MAX_VALUE :
        INFO = str(path_base) + "/info_" + str(TRLs) + "_" + ','.join(map(str, _CAPAS_COMPLETAS)) + "." + ''.join(map(str, _REDUCES))
    else :
        INFO = str(path_base) + "/info_" + str(TRLs) + "_" + str(BRC) + "_" + ','.join(map(str, _CAPAS_COMPLETAS)) + "." + ''.join(map(str, _REDUCES))

    _COMBINATION_REDUCES = _REDUCES[:]
    _REDUCES_normalizer  = _REDUCES[:]
    _CANDIDATO_REDUCES   = _REDUCES[:]

    # Denormalizes _CANDIDATO_REDUCES.
    for i in range (0, len(_REDUCES)) :
        if _REDUCES[i] > 0 :
            _CANDIDATO_REDUCES[i] += 1

    #######
    # BRC #
    #######

    # Initialize infos.
    check_call("rm -f " + str(INFO) + " " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle", shell=True)

    kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)
    rmse1D_first = rmse1D_antes

    while _CANDIDATO != _CAPAS_COMPLETAS and kbps_candidato[1] < BRC : # H_min < Ncapas_T
        # max_iteraciones -= 1
        # if max_iteraciones < 0 :
        #    check_call("echo \"" + "\nCompleted evaluations. There are layers that have not come to use, because it is not profitable to do so.\" >> " + str(INFO) + "_detalle", shell=True)
        #    exit (0)

        radian_candidato = -MAX_VALUE

        _CAPAS = _CANDIDATO[:] # upgrade _CAPAS
        _REDUCES = _CANDIDATO_REDUCES[:]
        # raw_input("actualiza _CAPAS: " + str(_CAPAS)) # !
        check_call("echo \"-> " + str(_CANDIDATO) + " * " + str(_CANDIDATO_REDUCES_normalized) + "\" >> " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle ; echo >> " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle", shell=True)

        emptyLayer = 0
        z = 0
        while z < len(_CAPAS) : # Walk each subband # In python, the 'For' can not change Z for emptyLayer.
            _COMBINATION = _CAPAS[:] # Initializes _COMBINATION
            _COMBINATION_REDUCES = _REDUCES[:]
            # raw_input("Initializes _COMBINATION: " + str(_COMBINATION) + "con REDUCES: " + str(_REDUCES)) # !
            # check_call("echo " + str(_COMBINATION_REDUCES),shell=True) # !
            # raw_input("") # !

            if z < TRLs : # TEXTURES

                if _REDUCES[z] > 0 : # reduces available
                    _COMBINATION_REDUCES[:TRLs] = [_REDUCES[z] - 1] * TRLs
                    if _COMBINATION[z] == 0 :
                        _COMBINATION[z] = 1 # At least one layer.
                    kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

                elif (_CAPAS[z] + emptyLayer) < Ncapas_T : # T available layers.
                    _COMBINATION[z] = _CAPAS[z] + 1 + emptyLayer
                    if _COMBINATION[z] < Ncapas_T :
                        _COMBINATION_REDUCES[:TRLs] = [Nclevels_T] * TRLs # Equally all subbands.
                    kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

                if _COMBINATION[z] == Ncapas_T :
                    emptyLayer = 0

            else : # MOTION

                if _REDUCES[z] > 0 : # reduces available
                    _COMBINATION_REDUCES[z] = _REDUCES[z] - 1 # Each field of motion independently.
                    if _COMBINATION[z] == 0 :
                        _COMBINATION[z] = 1 # Al menos una capa
                    kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

                elif (_CAPAS[z] + emptyLayer) < Ncapas_M : # M available layers.
                    _COMBINATION[z] = _CAPAS[z] + 1 + emptyLayer
                    if _COMBINATION[z] < Ncapas_M :
                        _COMBINATION_REDUCES[z] = Nclevels_M # Each field of motion independently.
                    kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

                if _COMBINATION[z] == Ncapas_M :
                    emptyLayer = 0


            if emptyLayer > 0 : # Repeat the evaluation of a subband until a layer that improves the RMSE (! = Empty layer).
                z -= 1
            z += 1

        # The new search parameters to fit the current situation.
        kbps_antes   = kbps_candidato[1]
        rmse1D_antes = rmse1D_candidato

        check_call("echo \"" + str(_CANDIDATO)+ " * " + str(_CANDIDATO_REDUCES_normalized) + CANDIDATO_KBPS + str(radian_candidato) + "\" >> " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_optimizado_BRCbruto", shell=True)

        # Could not find a candidate better than the proposed vector base (_COMBINATION)
        if _CAPAS == _CANDIDATO and _REDUCES == _CANDIDATO_REDUCES :

            rmse1D_antes = rmse1D_first
            check_call("echo \"" + "\nLa distorsion ha aumentado.\" >> " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle", shell=True)

        else :
            # Save AVERAGES
            AVERAGES, RMSEs = save_AVERAGES (iGOP, AVERAGES, RMSEs, kbps_candidato, rmse1D_candidato)

            # List of layer added (for gnuplot) _CAPAS y _CANDIDATO
            #for p in range (0, len(_CAPAS)-1) :
            #    if _CAPAS[p] != _COMBINATION[p] :
            #        _layerAdded[iGOP].append(p)
            #        break

    return AVERAGES, RMSEs#, _layerAdded




# 5) 13. A subband for all. PtAnterior.
#-------------------------------------------

## Sorting algorithm: Subband Removing R/D optimization (SR-opt). The
## computational cost of Algorithm FS-opt can be reduced if it is supposed
## that the contribution of each temporal subband to the minimization
## of the distortion of the reconstructed GOP is independent of the
## others.\n Thus, the contribution of a set of quality layers of a
## subband can be evaluated while the rest of subbands keep all
## layers.\n This idea has been implemented by removing a quality layer
## (and the rest of dependant layers) of a subband of the code-stream
## of a GOP, decompressing the GOP and computing the distortion.
#
#  @param iGOP GOP number of the current iteration.
#  @param FIRST_picture_ofGOP Number of the first image of the GOP.
#  @param pictures Total number of images to process. It may correspond to the images of a GOP, or all images in the sequence.
#  @param _CAPAS_COMPLETAS Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
#  @param AVERAGES Empty list of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @param RMSEs Empty list of distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @return Three lists of values as a result is obtained:
#  - Ordered list of layers from codestream.
#  - Mean kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
#  - Distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
def OneSub_ForAll_PtAnterior (iGOP, FIRST_picture_ofGOP, pictures, _CAPAS_COMPLETAS, AVERAGES, RMSEs) : # Evaluaciones -> Optimizado -> Detalle

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    # Variables
    _ENVIO_VACIO  = ([0] * len(_CAPAS_COMPLETAS))
    _ENVIOS       = []
    _EVALUACIONES = []
    _SUB_EVALUADA = []

    snr_fileA     = "low_0"
    snr_fileB     = "../low_0" + str(iGOP) # Each GOP is independent of the others.


    # 1. DEFINE ASSESSMENTS. Initialization _ENVIOS (variable describing shipments)
    for uu in range (0, len(_CAPAS_COMPLETAS)) :
        _ENVIOS.append(_ENVIO_VACIO[:])                                      # _SHIPPING
        _ENVIOS.append(_CAPAS_COMPLETAS[:])
        _SUB_EVALUADA.append(_ENVIO_VACIO[:])                                # _SUB_EVALUATED
        _SUB_EVALUADA.append(_ENVIO_VACIO[:])
        for u in range (0, _CAPAS_COMPLETAS[uu]+1) :
            _ENVIOS[len(_ENVIOS)-1][uu] = u                                  # _SHIPPING
            _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu] = 1                      # _SUB_EVALUATED
            if u < _CAPAS_COMPLETAS[uu] :
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])                   # _SHIPPING
                _SUB_EVALUADA.append(_SUB_EVALUADA[len(_SUB_EVALUADA)-1][:]) # _SUB_EVALUATED


    # 2. It tests ASSESSMENTS (extraction + reconstruction) resulting slopes (radian).
    for u in range (0, len(_ENVIOS)) :
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # RESPECT THE PREVIOUS ITEM, not referred to starting point.
        rmse1D_antes = rmse1D
        kbps_antes   = kbps_TM[1] # kbps @@@

        # Collect the results of evaluations: sending his radian.
        _EVALUACIONES.append([_ENVIOS[u][:], _SUB_EVALUADA[u][:], radian])



    # 4. ORDERED THE TEST ACCORDING TO PENDING.
    _EVALUACIONES.sort(key=lambda x:x[2], reverse=True) # Position laying order.
    # PRINT (depuration)
    check_call("mv " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle "
                     + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_evaluaciones"
                     , shell=True)
    check_call("echo \"" + "\n# ASSESSMENTS tested BEFORE, NOW AS ORDERED, SLOPE = RADIAN\n" + "\" >> "
                     + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_evaluaciones"
                     , shell=True)
    for u in range (0, len(_EVALUACIONES)) :
        check_call("echo \"" + str(_EVALUACIONES[u])  + "\" >> "
                     + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_evaluaciones"
                     , shell=True)



    # Deletes only the points for the calculation of angles and points that are at an angle = 0.
    u = 0
    longitud = len(_EVALUACIONES)
    while u < longitud : # You can not use a 'for', because you are changing the length of the vector that is crossed.
        if (0 in _EVALUACIONES[u][0]) or (0 == _EVALUACIONES[u][2]) :
            _EVALUACIONES.pop(u)
            longitud -= 1
        else :
            u += 1


    # If vectors before any texture send, forward the first shipment of textures.
    for u in range (0, len(_EVALUACIONES)) :
        if 1 in _EVALUACIONES[u][1][:TRLs] : # The first shipment of textures.
            if u != 0 :
                _EVALUACIONES.insert(0, _EVALUACIONES.pop(u)) # The first layer of textures that were to send, is placed at the beginning of the transmission, (could have before sending vectors).
            break


    # 5. EXPRESSING A NOTATION OF SHIPPING. Ignoring empty layers.
    _ENVIOS = [[0] * N_subbands]
    for u in range (0, len(_EVALUACIONES)) :
        if _ENVIOS[len(_ENVIOS)-1][_EVALUACIONES[u][1].index(1)] < _EVALUACIONES[u][0][_EVALUACIONES[u][1].index(1)] :
            _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:]) # Duplicates last element.
            _ENVIOS[len(_ENVIOS)-1][_EVALUACIONES[u][1].index(1)] = _EVALUACIONES[u][0][_EVALUACIONES[u][1].index(1)] # Add layer to send.

    # PRINT (depuration)
    for u in range (0, len(_ENVIOS)) :
        check_call("echo \"" + str(_ENVIOS[u])  + "\" >> "
                   + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_optimizado"
                   , shell=True)


    # . CHECK THE SHIPPING OPTIMIZADO. This code is not required, only serves to research tasks.
    _ENVIOS = _ENVIOS[1:][:]
    for u in range (0, len(_ENVIOS)) :
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # Save AVERAGES #
        AVERAGES, RMSEs = save_AVERAGES (iGOP, AVERAGES, RMSEs, kbps_TM, rmse1D)


    return AVERAGES, RMSEs






# 6) 10. Isolated Subband Removing.
#----------------------------------

## Sorting algorithm: Isolated Subband Removing R/D optimization
## (ISR-opt). The computational cost of Algorithm SR-opt can be reduced
## if the contribution of a set of quality layers of a subband can be
## computed regardless the contribution of the rest of subbands.
#
#  Example distortions one subband are compared. The original and the
#  reconstructed. This task is made with each subband. No motion
#  vectors in the process.
#
#  @param iGOP GOP number of the current iteration.
#  @param FIRST_picture_ofGOP Number of the first image of the GOP.
#  @param pictures Total number of images to process. It may correspond to the images of a GOP, or all images in the sequence.
#  @param _CAPAS_COMPLETAS Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
#  @param AVERAGES Empty list of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @param RMSEs Empty list of distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
#  @return Three lists of values as a result is obtained:
#  - Ordered list of layers from codestream.
#  - Mean kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
#  - Distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP. (Obtained from info.py).
def Sub_Independents (iGOP, FIRST_picture_ofGOP, pictures, _CAPAS_COMPLETAS, AVERAGES, RMSEs) :

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    # Variables
    _ENVIO_VACIO  = ([0] * len(_CAPAS_COMPLETAS))
    _ENVIOS       = []
    _EVALUACIONES = []
    _SUB_EVALUADA = []

    snr_fileA     = None
    snr_fileB     = None


    # 1. DEFINE ASSESSMENTS. Initialization _ENVIOS (variable describing shipments)
    for uu in range (0, (len(_CAPAS_COMPLETAS)/2)+1) : # para las texturas, los vectores no se evaluan
        _ENVIOS.append(_ENVIO_VACIO[:])                                       # _SHIPPING
        _SUB_EVALUADA.append(_ENVIO_VACIO[:])                                 # _SUB_EVALUATED
        for u in range (0, _CAPAS_COMPLETAS[uu]) :
            _ENVIOS[len(_ENVIOS)-1][uu] += 1                                  # Updates the last element.
            _SUB_EVALUADA[len(_SUB_EVALUADA)-1][uu] = 1                       # _SUB_EVALUATED
            if u < _CAPAS_COMPLETAS[uu]-1 :
                _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:])                    # _SHIPPING. Duplicates the last element.
                _SUB_EVALUADA.append(_SUB_EVALUADA[len(_SUB_EVALUADA)-1][:])  # _SUB_EVALUATED

    # Displays information about the execution:
    # print '\n'.join(map(str, _ENVIOS))
    # print '\n'.join(map(str, _SUB_EVALUADA))


    # 2. It tests ASSESSMENTS (extraction + reconstruction) resulting slopes (radian).

    for u in range (0, len(_ENVIOS)) :

        # UPDATE the comparison of SNR, each time you change the lba subband (between _ENVIO_VACIO)
        # snr_fileA=low_4 snr_fileB=../low_4 ; snr_fileA=high_4 snr_fileB=../high_4 ; snr_fileA=high_3 snr_fileB=../high_3 ; snr_fileA=high_2 snr_fileB=../high_2 ; snr_fileA=high_1 snr_fileB=../high_1
        _sub_sent = [[i for i, x in enumerate(_ENVIOS[u]) if x != e] for e in [0]]
        if _sub_sent[0][0] == 0 :
            snr_fileA = "low_" + str(TRLs-1)
        else :
            snr_fileA = "high_" + str(TRLs-_sub_sent[0][0])
        snr_fileB = "../" + snr_fileA
        #print str(_sub_sent[0][0]) + " " + str(snr_fileA) + " " + str(snr_fileB)

        # CHECK
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # ESPECT THE PREVIOUS ITEM, not referred to starting point. CODE IS NOT BRC (updated only with candidates), this serves for sub_independientes and UnaParaTodas_PtAnterior
        rmse1D_antes = rmse1D
        kbps_antes   = kbps_TM[1] # kbps @@@

        # Collect the results of evaluations: sending his radian.
        _EVALUACIONES.append([_ENVIOS[u][:], _SUB_EVALUADA[u][:], radian])


    # 4. ORDERED THE TEST ACCORDING TO SLOPE (radian).
    _EVALUACIONES.sort(key=lambda x:x[2], reverse=True) # Position laying order.
    # PRINT (depuracion)
    check_call("mv " + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_detalle "
                     + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_evaluaciones"
                     , shell=True)
    check_call("echo \"" + "\n# ASSESSMENTS tested BEFORE, NOW AS ORDERED, SLOPE = RADIAN\n" + "\" >> "
                     + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_evaluaciones"
                     , shell=True)
    for u in range (0, len(_EVALUACIONES)) :
        check_call("echo \"" + str(_EVALUACIONES[u])  + "\" >> "
                     + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_evaluaciones"
                     , shell=True)


    # Deletes only the points for the calculation of angles and points that are at an angle = 0.
    u = 0
    longitud = len(_EVALUACIONES)
    while u < longitud : # You can not use a 'for', because you are changing the length of the vector that is crossed.
        if 0 == _EVALUACIONES[u][2] :
            _EVALUACIONES.pop(u)
            longitud -= 1
        else :
            u += 1


    # 4.5 Generates motion vectors.
    _ENVIOS       = []
    _SUB_EVALUADA = []
    for u in range (TRLs, len(_CAPAS_COMPLETAS)) :   # For vectors.
        _ENVIOS.append(_ENVIO_VACIO[:])              # _SHIPPING
        _SUB_EVALUADA.append(_ENVIO_VACIO[:])        # _SUB_EVALUATED
        _ENVIOS[len(_ENVIOS)-1][u] = 1               # Updates the last element.
        _SUB_EVALUADA[len(_SUB_EVALUADA)-1][u] = 1   # _SUB_EVALUATED
    # Add vectors into _EVALUACIONES
    for u in range (0, len(_ENVIOS)) :
        _EVALUACIONES.insert(u+1, [_ENVIOS[u][:], _SUB_EVALUADA[u][:], "radian_no_calculado"])

    # Displays information about the execution:
    #print '\n'.join(map(str, _ENVIOS))
    #print '\n'.join(map(str, _SUB_EVALUADA))
    #print '\n'.join(map(str, _EVALUACIONES))


    # 5. EXPRESSING A NOTATION OF SHIPPING. Ignoring empty layers.
    _ENVIOS = [[0] * N_subbands]
    for u in range (0, len(_EVALUACIONES)) :
        if _ENVIOS[len(_ENVIOS)-1][_EVALUACIONES[u][1].index(1)] < _EVALUACIONES[u][0][_EVALUACIONES[u][1].index(1)] :
            _ENVIOS.append(_ENVIOS[len(_ENVIOS)-1][:]) # Doubles last element.
            _ENVIOS[len(_ENVIOS)-1][_EVALUACIONES[u][1].index(1)] = _EVALUACIONES[u][0][_EVALUACIONES[u][1].index(1)] # Add layer to send.


    # PRINT (depuration)
    for u in range (0, len(_ENVIOS)) :
        check_call("echo \"" + str(_ENVIOS[u])  + "\" >> "
                   + str(INFO) + "_GOP" + str(iGOP) + "de" + str(GOPs) + "_optimizado"
                   , shell=True)

    # Displays information about the execution:
    #check_call("echo \"" + "_EVALUACIONES: " + str(_EVALUACIONES)  + "\"", shell=True)
    #exit (0)


    # . CHECK THE SHIPPING OPTIMIZADO. This code is not required, only serves to research tasks.
    snr_fileA = "low_0"
    snr_fileB = "../low_0" + str(iGOP) # Each GOP is independent of the others.
    _ENVIOS = _ENVIOS[1:][:]

    for u in range (0, len(_ENVIOS)) :
        _COMBINATION = _ENVIOS[u][:]
        kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

        # Save AVERAGES #
        AVERAGES, RMSEs = save_AVERAGES (iGOP, AVERAGES, RMSEs, kbps_TM, rmse1D)




    # . Removes the first GOP. For the SNR, compare only the IGOP treaty.
    namefile = str(path_base) + "/low_" + str(TRLs-1)
    p = sub.Popen("dd"
                  + " if="    + namefile
                  + " of="    + namefile + "_temp"
                  + " skip="  + str(1)
                  + " bs="    + str(int(pixels_in_x * pixels_in_y * 1.5)) # Image size.
                  , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
    out, err = p.communicate()

    p = sub.Popen("mv " + namefile + "_temp " + namefile, shell=True, stdout=sub.PIPE, stderr=sub.PIPE) # dd no sobreescribe ficheros, por eso es necesario el temporal.
    out, err = p.communicate()


    for trl in range (1, TRLs) :
        namefile = str(path_base) + "/high_" + str(trl)
        p = sub.Popen("dd"
                      + " if="    + namefile
                      + " of="    + namefile + "_temp"
                      + " skip="  + str(GOP_size / pow(2, trl))
                      + " bs="    + str(int(pixels_in_x * pixels_in_y * 1.5)) # Image size.
                      , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        out, err = p.communicate()

        p = sub.Popen("mv " + namefile + "_temp " + namefile, shell=True, stdout=sub.PIPE, stderr=sub.PIPE) # dd no sobreescribe ficheros, por eso es necesario el temporal.
        out, err = p.communicate()

    return AVERAGES, RMSEs





## A direct transcoding. Direct transcoding video, (treating the
## sequence as a whole).
#  @param combination List some specific numbers of layers for each subband.
#  @return Video transcoded.
def direct_transcode_video (combination) :

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    FIRST_picture_ofGOP = 0
    pictures            = GOPs * GOP_size + 1
    GOPs_to_expand      = GOPs
    iGOP                = 1

    snr_fileA           = "low_0"
    snr_fileB           = "../low_0" # Here it does not exist "../low_0_original" or "../low_0+iGOP"

    #_COMBINATION = [1, 1, 1, 1, 1, 1, 1, 1, 1]
    #_COMBINATION = _CAPAS_COMPLETAS[:]
    _COMBINATION = map(int, combination.split(','))

    kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

    # PRINT a file # info.py  is applied to the entire video, namely, the average is already done.
    check_call("echo \"" + str(kbps_TM[1]) + "\t " + str(rmse1D) + "\t " + "\t" + str(_COMBINATION) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages_gnuplot", shell=True)

    return 0



## A direct transcoding. Direct transcoding video, (treating the
## sequence gop to gop).
#  @param combination List some specific numbers of layers for each subband.
#  @return Video transcoded.
def direct_transcode_gop (_COMBINATION) :

    # Variables of the LBA function (python calls declare).
    kbps_TM = kbps_TM_average = rmse1D = kbps_antes = radian = radian_candidato = kbps_candidato = rmse1D_candidato = emptyLayer = KBPS_DATA = CANDIDATO_KBPS = 0
    _CANDIDATO = _CANDIDATO_REDUCES = _CANDIDATO_REDUCES_normalized = []
    rmse1D_antes = MAX_VALUE

    snr_fileA = "low_0"
    snr_fileB = "../low_0" + str(iGOP) # Each GOP is independent of the others.

    kbps_TM, kbps_TM_average, rmse1D, kbps_antes, rmse1D_antes, radian, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, KBPS_DATA, CANDIDATO_KBPS = lba(FIRST_picture_ofGOP, iGOP, pictures, kbps_antes, rmse1D_antes, radian_candidato, kbps_candidato, rmse1D_candidato, _CANDIDATO, _CANDIDATO_REDUCES, _CANDIDATO_REDUCES_normalized, emptyLayer, CANDIDATO_KBPS, _COMBINATION, _COMBINATION_REDUCES, snr_fileA, snr_fileB)

    # PRINT a file # info.py  is applied to the entire video, namely, the average is already done.
    check_call("echo \"" + str(kbps_TM[1]) + "\t " + str(rmse1D) + "\t " + "\t" + str(_COMBINATION) + "\" >> " + str(INFO) + "_" + str(GOPs) + "GOPs" + "_averages_gnuplot", shell=True)

    return 0






#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------
#- MAIN ---------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------


# Path
#--------------------

## Current path.
p = sub.Popen("echo $PWD", shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
out, err     = p.communicate()
## Codestream path.
path_base    = out[:-1]
## Truncated codestream path.
path_extract = path_base + "/extract"
## Reconstruction path.
path_tmp     = path_base + "/tmp"


# Inicialization
#--------------------

## Number of subbands.
N_subbands = (TRLs * 2) - 1
## Initializes the class GOP (Group Of Pictures).
gop        = GOP()
## Extract the value of the size of a GOP, that is, the number of images.
GOP_size   = gop.get_size(TRLs)
## Number of images to process.
pictures   = GOPs * GOP_size + 1
## Number of the first image of the GOP, in the overall sequence of images.
FIRST_picture_ofGOP = 0
# fields    = pictures / 2

## Duration of the sequence.
duration   = pictures / (FPS * 1.0)
## Original sequence or part of it. This is not the video stream but a link to it.
snr_fileA  = None
## Reconstruction of a codestream or part of it. This is not the video stream but a link to it.
snr_fileB  = None

# Variables
#--------------------

## First subband H, in _COMBINATION list; which lists each subband and field of motion.
H_max      = 1
## First field of motion, in _COMBINATION list; which lists each subband and field of motion.
M_max      = TRLs
## Maximum amount you reduce available for textures. Also subject to the separability of the whole number blocks_in_x and blocks_in_y.
Nclevels_T = 0 # 
## Maximum amount you reduce available for vector motions. Also subject to the separability of the whole number blocks_in_x and blocks_in_y.
Nclevels_M = 0 # 1
## Number of layers of vectors. Its default value is 1. Scalability in a field of motion has not proved useful.
Ncapas_M   = 1


#max_iteraciones = (TRLs * Ncapas_T * (Nclevels_T+1)) + (((TRLs-1) * Ncapas_M) * (Nclevels_M+1))

# Function parameters.
#---------------------

## Rate value of 'Y' component of each subband. It is not used, and therefore, its default value is 0. This is useful for research tasks.
_RATES_Y = [[0] for x in xrange (TRLs)]
## Rate value of 'U' component of each subband. It is not used, and therefore, its default value is 0. This is useful for research tasks.
_RATES_U = [[0] for x in xrange (TRLs)]
## Rate value of 'V' component of each subband. It is not used, and therefore, its default value is 0. This is useful for research tasks.
_RATES_V = [[0] for x in xrange (TRLs)]

## Number of images to process.
pics = pictures
for z in range (1, TRLs) :
    pics = (pics + 1) / 2
    for image_number in range (0, pics-2) :
        _RATES_Y[TRLs-z].append(0)
        _RATES_U[TRLs-z].append(0)
        _RATES_V[TRLs-z].append(0)


## Total number of layers of the codestream for each subband. Usually all subbands have the same number of layers.
_CAPAS_COMPLETAS = ([Ncapas_T] * TRLs) + ([Ncapas_M] * (TRLs-1))


## List of distortions for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
RMSEs            = [[] for x in xrange (GOPs + 1)] # rmse: [[GOP0],                                   <- None
                                                   #        [GOP1], ..., [GOPn],                      <- RMSE as many points on the curve of each GOP.
                                                   #        [Unweighted average of GOP 1 to N]]


## List of means kilobits per second, for each GOP, each truncated codestream result of a sorting algorithm GOP to GOP.
AVERAGES         = [[] for x in xrange (GOPs + 1)] # kbps: [[GOP0],                                   <- Kbps as many points in the curve of each GOP0.
                                                   #        [GOP1], ..., [GOPn],                      <- Kbps as many points in the curve of each GOP.
                                                   #        [Unweighted average of GOP 1 to N],
                                                   #        [Weighted average of GOP 0 and N]]

# Ej. AVERAGES[iGOP][kbps_punto].
#
# Ej para 1 GOP [[10860.9, 22089.8], [2530.2, 3472.6], [2530.2, 3472.6], [3020.2, 4567.7]]
#               [[     GOP0       ], [     GOP1     ], [   Media 1aN  ], [  Media Final ]]
#               [[Punto1 , Punto2 ], [Punto1, Punto2], [Punto1, Punto2], [Punto1, Punto2]]
#
# GOP1 curve:                     AVERAGES[1][0] <- Point 1 of the curve.
#                                 AVERAGES[1][1] <- Point 2 of the curve.
# The average curve of the video: AVERAGES[3][0] <- Point 1 of the curve.
#                                 AVERAGES[3][1] <- Point 2 of the curve.



# Variable from functions, python declare requests.
#--------------------------------------------------

## Kbps detail of a truncated codestream. Indicandos sizes for each subband and motion field.
KBPS_DATA        = ""
## Kbps detail of a truncated codestream. Indicandos sizes for each subband and motion field. Which is better in terms rate / distortion, found so far in the course of a sorting algorithm.
CANDIDATO_KBPS   = ""

## Kbps of the last codestream truncated analyzed so far.
kbps_antes       = 0
## A truncated codestream kbps, which is better in terms rate / distortion, found so far in the course of a sorting algorithm.
kbps_candidato   = [0, 0]
## Kbps of codestream truncation of the current GOP.
kbps_TM          = [0, 0]
## Distortion of a codestream, truncated or not, currently analyzed.
rmse1D           = 0
## Distortion of a codestream, truncated or not, discussed above.
rmse1D_antes     = MAX_VALUE
## Distortion of the best truncated codestream, which is better in terms rate / distortion, found so far in the course of a sorting algorithm.
rmse1D_candidato = 0

## Index that relates the values of rate and distortion. Which is better codestream in terms rate / distortion, found so far in the course of a sorting algorithm.
radian_candidato = -MAX_VALUE
## Index that relates the values of rate and distortion.
radian           = 0

## Binary index that indicates whether a codestream, truncated or not, has empty layers.
emptyLayer       = 0
#_layerAdded      = [[] for x in xrange (GOPs)]

## An empty codestream.
_CEROS           = [0] * N_subbands
## Best truncated codestream found to a certain rate.
_CAPAS           = [0] * N_subbands
## The current truncated codestream.
_COMBINATION     = [0] * N_subbands
## Best truncated codestream found at so far.
_CANDIDATO       = [0] * N_subbands

#_CAPAS_VACIAS = # for optimization.


# This form initialize a list works for one list but not on a list of lists.
#---------------------------------------------------------------------------

## Values reduction in spatial resolution, for each subband.
_COMBINATION_REDUCES            = ([Nclevels_T+1] * TRLs) + ([Nclevels_M+1] * (TRLs-1)) # +1 pq el BRC primero modifica y despues evalua
## Values reduction in spatial resolution, for each subband.
_CANDIDATO_REDUCES              = _COMBINATION_REDUCES[:]
## Maximum reductions in spatial resolution that can be applied.
_REDUCES_normalizer             = ([Nclevels_T] * TRLs) + ([Nclevels_M] * (TRLs-1))
## Maximum reductions in spatial resolution that can be applied. 
_CANDIDATO_REDUCES_normalized   = []
## Maximum reductions in spatial resolution that can be applied. 
_COMBINATION_REDUCES_normalized = []


# Initializes _REDUCES.
#----------------------

## Values reduction in spatial resolution, for each subband.
_REDUCES = map(int, discard_SRLs.split(','))

## Indicates if the user has specified values of spatial resolutions that do not fit the specified number of TLRs.
error = False
if len(_REDUCES) != N_subbands :
    check_call("echo discard_SRLs: its length must be " + str(N_subbands) + " with TRL=" + str(TRLs) + ".", shell=True) # Types
    error = True
#if que no supere Nclevels_M ni Nclevels_T

if error == True :
    _REDUCES = [0] * N_subbands #_REDUCES = ([Nclevels_T] * TRLs) + ([Nclevels_M] * (TRLs-1))
    check_call("echo discard_SRLs default = " + str(_REDUCES) + "   Press ENTER to continue...", shell=True) # Types

if BRC == MAX_VALUE :
    ## Path log files execution.
    INFO = str(path_base) + "/info_" + str(TRLs) + "_" + ','.join(map(str, _CAPAS_COMPLETAS)) + "." + ''.join(map(str, _REDUCES))
else :
    INFO = str(path_base) + "/info_" + str(TRLs) + "_" + str(BRC) + "_" + ','.join(map(str, _CAPAS_COMPLETAS)) + "." + ''.join(map(str, _REDUCES))

_COMBINATION_REDUCES = _REDUCES[:]
_REDUCES_normalizer  = _REDUCES[:]
_CANDIDATO_REDUCES   = _REDUCES[:]

# Denormalizes _CANDIDATO_REDUCES
for i in range (0, len(_REDUCES)) :
    if _REDUCES[i] > 0 :
        _CANDIDATO_REDUCES[i] += 1



# SORTING ALGORITHMS.
#--------------------
# There are 2 types of sorting algorithms:
# A) Manages the full video.
# B) Manages the video GOP to GOP.



# A) Manages the full video.
#---------------------------
#---------------------------

FIRST_picture_ofGOP = 0
pictures            = GOPs * GOP_size + 1
## Number of GOPs to expand. Depending on the chosen algorithm
## ordination, will have value 1 or the total number of
## GOPs. Additionally can expand a subset of the sequence of GOPs.
GOPs_to_expand      = GOPs

if algorithm == "transcode_video" :
    # A direct transcoding.
    direct_transcode_video (combination)
    exit (0)

elif algorithm == "ITS" :
    check_call("echo A\) Independents transmission by Subbands. 'lowx' and '../low_x'", shell=True)
    MCJ2K_for_Subbands__rmse_lowx (_CAPAS_COMPLETAS)
    exit (0)

elif algorithm == "PTS" :
    check_call("echo 1\) Progressive Transmission by Subbands \(PTS\). 'low0' and '../low_0' \(full video\).", shell=True)
    for_Subbands__rmse_low0 (_CAPAS_COMPLETAS)
    exit (0)

elif algorithm == "PTL" :
    check_call("echo 2\) Progressive Transmission by Layers \(PTL\). For Layers.", shell=True)
    for_Layers (_CAPAS_COMPLETAS)
    exit (0)

elif algorithm == "AmPTL" :
    check_call("echo 3\) Attenuation-modulated PTL \(AmPTL\). Layers ordered by gains.", shell=True)
    Gains_Layers (_CAPAS_COMPLETAS)
    exit (0)



# B) Manages the video GOP to GOP.
#---------------------------------
#---------------------------------
p = sub.Popen("mv " + str(path_base) + "/low_0 " + str(path_base) + "/low_0_original"
              , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
out, err = p.communicate()

for iGOP in range (1, GOPs+1) : # iGOP = 1 ie GOP 1 (GOP 0, have the first L only)
    # Initial and Final image of the GOP treated (iGOP).
    FIRST_picture_ofGOP =  (iGOP - 1) * GOP_size
    pictures            =   iGOP      * GOP_size + 1

    # 3� y 4�
    #FIRST_picture_ofGOP =  (3   - 1) * GOP_size
    #pictures            =   4        * GOP_size + 1

    # 1�, 2� y 3�
    #FIRST_picture_ofGOP =  0
    #pictures            =  3         * GOP_size + 1

    GOPs_to_expand = ((pictures-1) - FIRST_picture_ofGOP) / GOP_size # GOPs_to_expand = 1, to extract a GOP only.

    # Divide the original video, according to the GOPs handled.
    p = sub.Popen("dd"
                  + " if="    + str(path_base) + "/low_0_original"
                  + " of="    + str(path_base) + "/low_0" + str(iGOP)
                  + " skip="  + str(GOP_size * (iGOP - 1))                # Jump to the current GOP. Number of images of a GOP * IGOP.
                  + " bs="    + str(int(pixels_in_x * pixels_in_y * 1.5)) # Image size.
                  + " count=" + str((GOP_size * GOPs_to_expand) + 1)      # Number of GOPs to expand. (GOPs_to_expand)
                  , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
    out, err = p.communicate()

    if algorithm == "transcode_gops" :
        # Send to each gop.
        _ENVIOS = [[6, 7, 6, 6, 6, 1, 1, 0, 0],
                   [6, 6, 3, 0, 0, 1, 1, 0, 0],
                   [6, 4, 2, 0, 0, 1, 1, 0, 0],
                   [6, 5, 3, 0, 0, 1, 1, 0, 0],
                   [6, 6, 3, 0, 0, 1, 1, 0, 0],
                   [6, 5, 5, 5, 0, 1, 1, 0, 0],
                   [6, 6, 5, 5, 0, 1, 1, 0, 0],
                   [6, 5, 4, 0, 0, 1, 1, 0, 0]]
        
        _COMBINATION = _ENVIOS[iGOP-1][:]
        # A direct transcoding of each gop.
        direct_transcode_gop (_COMBINATION)

        p = sub.Popen("mv " + str(path_extract) + " " + str(path_extract) + "_GOP" + str(iGOP)
                      , shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        out, err = p.communicate()
        #errcode = p.returncode

    elif algorithm == "FS" :
        check_call("echo 4\) Full Search R/D optimization \(FS-opt\).", shell=True)
        AVERAGES, RMSEs = BRC_BruteForce (iGOP, FIRST_picture_ofGOP, pictures, _CAPAS_COMPLETAS, AVERAGES, RMSEs) #, _layerAdded)

    elif algorithm == "SR" :
        check_call("echo 5\) Subband Removing R/D optimization \(SR-opt\).", shell=True)
        AVERAGES, RMSEs = OneSub_ForAll_PtAnterior (iGOP, FIRST_picture_ofGOP, pictures, _CAPAS_COMPLETAS, AVERAGES, RMSEs)

    elif algorithm == "ISR" :
        check_call("echo 6\) Isolated Subband Removing R/D optimization \(ISR-opt\).", shell=True)
        AVERAGES, RMSEs = Sub_Independents (iGOP, FIRST_picture_ofGOP, pictures, _CAPAS_COMPLETAS, AVERAGES, RMSEs)

    else :
        check_call("Parameter algorithm unknown.")
        exit (0)





# Collect the means of each GOP.
#-------------------------------
AVERAGES, RMSEs = averages_1toN (AVERAGES, RMSEs)
AVERAGES        = averages_0yN  (AVERAGES)
AVERAGES, RMSEs = averages_file (AVERAGES, RMSEs) #, _layerAdded)





'''
Los experimentos son:
############################################################################################################################################################################################

Proceso de todas las imágenes simultáneamente
-------------------------------------------------------------------------------------------------
A) MCJ2K (TRLs=5) contra lowx
   Sub0 contra Sub0; Sub0+Sub1 contra Sub0+Sub1; ...
   Por adición de subbandas comparando sólo con dichas subbandas extraidas (no con la reconstrucción completa)
B) MJ2K  (TRLs=1) 
   de las imágenes que se corresponderían con las subbandas

0) Compress/expand. Slopes con/sin GAINS
   slopes Gains. Con y SIN ganancias. contra low0
   Comprimir con 16 capas y descomprimirlas todas (con capas pero sin usarlas). Sacar X puntos con slopes distantes a 256. (Y el resto de experimentos con ganancias siempre)
1) Progressive Transmission by Subbands (PTS)
   For subbands contra low0
   Niveles subbandas Todo L4 capa a capa, M4, todo H3 capa a capa, M3, todo H2 capa a capa, M2, ...
   Es decir: 1capa_L4, 2capa_L4, 3capa_L4, ... M4, 1capa_H4, 2capa_H4, 3capa_H4, ... , M3, 
2) Progressive Transmission by Layers (PTL)
   For layers contra low0
   Niveles de capas (E) todas las primeras capas de cada subbanda, todos los vectores, las segundas, las terceras....
   Es decir: 1capa_L4, M4, 1capa_H4, M3, 1capa_H3, M2, 1capa_H2, M1, 1capa_H1, 2capa_L4, 2capa_H4, 2capa_H3, 2capa_H2, 2capa_H1, 3capa_L4, 3capa_H4, ....
3) Attenuation-modulated PTL (AmPTL) 
   Layers ordered by gains

Proceso gop a gop independientemente
-------------------------------------------------------------------------------------------------
4) Full Search R/D optimization (FS-opt)
5) Subband Removing R/D optimization (SR-opt) (experimento 13)
   13  (a pelo)
   13d (mejorado) escalado e importancia vectores
6) Isolated Subband Removing R/D optimization (ISR-opt)
   subbandas independientes
'''


'''
            #############################################
            check_call("echo \"" 
                       + " rmse1D_antes " + str(rmse1D_antes) 
                       + " rmse1D " + str(rmse1D) 
                       + " kbps_TM[0] " + str(kbps_TM[0]) 
                       + " kbps_TM[1] " + str(kbps_TM[1]) 
                       + " kbps_antes " + str(kbps_antes) 
                       + "\""
                       , shell=True)
            #############################################
'''


'''
FULL SEARCH 100KBPS MOBILE. Each gop.
_ENVIOS = [[7, 6, 5, 0, 0, 1, 1, 0, 0],
           [7, 6, 5, 0, 0, 1, 1, 0, 0],
           [7, 6, 6, 0, 0, 1, 1, 0, 0],
           [7, 6, 0, 0, 0, 1, 1, 0, 0],
           [7, 6, 0, 0, 0, 1, 1, 0, 0],
           [7, 6, 0, 0, 0, 1, 1, 0, 0],
           [7, 6, 6, 0, 0, 1, 1, 0, 0],
           [7, 6, 0, 0, 0, 1, 1, 0, 0]]


FULL SEARCH 200KBPS CITY. Each gop.
_ENVIOS = [[7, 7, 7, 0, 0, 1, 1, 1, 0],
           [7, 7, 7, 0, 0, 1, 1, 1, 0],
           [7, 7, 7, 7, 0, 1, 1, 1, 0],
           [8, 7, 7, 0, 0, 1, 1, 0, 0],
           [7, 7, 7, 7, 0, 1, 1, 1, 0],
           [7, 7, 7, 0, 0, 1, 1, 1, 0],
           [7, 7, 4, 0, 0, 1, 1, 1, 0],
           [7, 7, 6, 6, 0, 1, 1, 1, 0]]


FULL SEARCH 500KBPS PARKRUN. Each gop.
_ENVIOS = [[6, 7, 6, 6, 6, 1, 1, 0, 0],
           [6, 6, 3, 0, 0, 1, 1, 0, 0],
           [6, 4, 2, 0, 0, 1, 1, 0, 0],
           [6, 5, 3, 0, 0, 1, 1, 0, 0],
           [6, 6, 3, 0, 0, 1, 1, 0, 0],
           [6, 5, 5, 5, 0, 1, 1, 0, 0],
           [6, 6, 5, 5, 0, 1, 1, 0, 0],
           [6, 5, 4, 0, 0, 1, 1, 0, 0]]

FULL SEARCH 1000KBPS CROWDRUN. Each gop.
_ENVIOS = [[6, 6, 5, 5, 0, 1, 1, 0, 0],
           [6, 6, 5, 6, 0, 1, 1, 0, 0],
           [6, 6, 5, 6, 0, 1, 1, 0, 0],
           [6, 6, 5, 6, 0, 1, 1, 0, 0],
           [6, 6, 5, 6, 6, 1, 1, 0, 0],
           [6, 6, 5, 6, 0, 1, 1, 0, 0],
           [6, 6, 5, 6, 7, 1, 1, 0, 0],
           [6, 6, 5, 6, 6, 1, 1, 0, 0]]

'''
