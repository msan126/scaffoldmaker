"""
Generates a single 3-D colon segment with a simple
mesentery mesh along a central line, with variable
numbers of elements around, along and through wall,
with variable radius and thickness along.
"""

import math
from scaffoldmaker.annotation.annotationgroup import AnnotationGroup
from scaffoldmaker.meshtypes.meshtype_3d_colonsegmentteniacoli1 import sampleHaustrum, getuListFromOuterLengthProfile
from scaffoldmaker.meshtypes.scaffold_base import Scaffold_base
from scaffoldmaker.utils.geometry import createCirclePoints
from scaffoldmaker.utils.meshrefinement import MeshRefinement
from scaffoldmaker.utils import tubemesh
from scaffoldmaker.utils import interpolation as interp

class MeshType_3d_colonsegmentsimplemesentery1(Scaffold_base):
    '''
    Generates a single 3-D colon segment with simple mesentery mesh
    with variable numbers of elements around, along the central line,
    and through wall. The cross-section profile of the colon
    segment is largely cylindrical due to the lack of a tenia coli.
    '''
    @staticmethod
    def getName():
        return '3D Colon Segment Simple Mesentery 1'

    @staticmethod
    def getParameterSetNames():
        return [
            'Default',
            'Mouse 1']

    @staticmethod
    def getDefaultOptions(parameterSetName='Default'):
        return {
            'Number of elements around mesenteric zone' : 2,
            'Number of elements around non-mesenteric zone' : 8,
            'Number of elements along segment' : 4,
            'Number of elements through wall' : 1,
            'Start inner radius': 0.094,
            'Start radius derivative': 0.0,
            'End inner radius': 0.094,
            'End radius derivative': 0.0,
            'Start mesenteric zone width': 0.08,
            'Start mesenteric zone width derivative': 0.0,
            'End mesenteric zone width': 0.08,
            'End mesenteric zone width derivative': 0.0,
            'Segment length': 1.5,
            'Wall thickness': 0.055,
            'Use cross derivatives' : False,
            'Use linear through wall' : True,
            'Refine' : False,
            'Refine number of elements around' : 1,
            'Refine number of elements along segment' : 1,
            'Refine number of elements through wall' : 1
        }

    @staticmethod
    def getOrderedOptionNames():
        return [
            'Number of elements around mesenteric zone',
            'Number of elements around non-mesenteric zone',
            'Number of elements along segment',
            'Number of elements through wall',
            'Start inner radius',
            'Start radius derivative',
            'End inner radius',
            'End radius derivative',
            'Start mesenteric zone width',
            'Start mesenteric zone width derivative',
            'End mesenteric zone width',
            'End mesenteric zone width derivative',
            'Segment length',
            'Wall thickness',
            'Use cross derivatives',
            'Use linear through wall',
            'Refine',
            'Refine number of elements around',
            'Refine number of elements along segment',
            'Refine number of elements through wall'
        ]

    @staticmethod
    def checkOptions(options):
        for key in [
            'Number of elements along segment',
            'Number of elements through wall',
            'Refine number of elements around',
            'Refine number of elements along segment',
            'Refine number of elements through wall']:
            if options[key] < 1:
                options[key] = 1
        if options['Number of elements around mesenteric zone'] < 2:
            options['Number of elements around mesenteric zone'] = 2
        if options['Number of elements around non-mesenteric zone'] < 4:
            options['Number of elements around non-mesenteric zone'] = 4
        for key in [
            'Number of elements around mesenteric zone',
            'Number of elements around non-mesenteric zone']:
            if options[key] % 2 > 0:
                options[key] = options[key] + 1
        for key in [
            'Start inner radius',
            'End inner radius',
            'Start mesenteric zone width',
            'End mesenteric zone width',
            'Segment length',
            'Wall thickness']:
            if options[key] < 0.0:
                options[key] = 0.0
        for key in [
            'Start mesenteric zone width',
            'End mesenteric zone width'
            ]:
            if options[key] < 10.0*math.pi/180.0*min(options['Start inner radius'], options['End inner radius']):
                options[key] = round(10.0*math.pi/180.0*min(options['Start inner radius'], options['End inner radius']), 2)
        if options['Start mesenteric zone width'] > math.pi*0.5*options['Start inner radius']:
                options['Start mesenteric zone width'] = round(math.pi*0.5*options['Start inner radius'], 2)
        if options['End mesenteric zone width'] > math.pi*0.5*options['End inner radius']:
            options['End mesenteric zone width'] = round(math.pi*0.5*options['End inner radius'], 2)

    @staticmethod
    def generateBaseMesh(region, options):
        """
        Generate the base tricubic Hermite mesh. See also generateMesh().
        :param region: Zinc region to define model in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        :return: None
        """
        elementsCountAroundMZ = options['Number of elements around mesenteric zone']
        elementsCountAroundNonMZ = options['Number of elements around non-mesenteric zone']
        elementsCountAround = elementsCountAroundMZ + elementsCountAroundNonMZ
        elementsCountAlongSegment = options['Number of elements along segment']
        elementsCountThroughWall = options['Number of elements through wall']
        startRadius = options['Start inner radius']
        startRadiusDerivative = options['Start radius derivative']
        endRadius = options['End inner radius']
        endRadiusDerivative = options['End radius derivative']
        segmentLength = options['Segment length']
        startMZWidth = options['Start mesenteric zone width']
        startMZWidthDerivative = options['Start mesenteric zone width derivative']
        endMZWidth = options['End mesenteric zone width']
        endMZWidthDerivative = options['End mesenteric zone width derivative']
        wallThickness = options['Wall thickness']
        useCrossDerivatives = options['Use cross derivatives']
        useCubicHermiteThroughWall = not(options['Use linear through wall'])
        segmentCount = 1

        cx = [ [ 0.0, 0.0, 0.0 ], [ segmentLength, 0.0, 0.0 ] ]
        cd1 = [ [ segmentLength, 0.0, 0.0 ], [ segmentLength, 0.0, 0.0 ] ]
        cd2 = [ [ 0.0, 1.0, 0.0 ], [ 0.0, 1.0, 0.0 ] ]
        cd12 = [ [0.0, 0.0, 0.0 ], [ 0.0, 0.0, 0.0 ] ]

        # Generate variation of radius and mesenteric width along length
        radiusList = [startRadius, endRadius]
        dRadiusList = [startRadiusDerivative, endRadiusDerivative]
        mzWidthList = [startMZWidth, endMZWidth]
        dMZWidthList = [startMZWidthDerivative, endMZWidthDerivative]

        # Create object
        tubeMeshSegmentInnerPoints = TubeMeshSegmentInnerPointsNoTeniaColi(region, elementsCountAroundMZ, elementsCountAroundNonMZ, elementsCountAlongSegment,
            segmentLength, wallThickness)

        # Generate tube mesh
        annotationGroups, nextNodeIdentifier, nextElementIdentifier, xList, d1List, d2List, d3List, sx, curvatureAlong, factorList, uList, _, _ = tubemesh.generatetubemesh(region,
           elementsCountAround, elementsCountAlongSegment, elementsCountThroughWall, segmentCount, cx, cd1, cd2, cd12,
           radiusList, dRadiusList, mzWidthList, dMZWidthList, tubeMeshSegmentInnerPoints, wallThickness, segmentLength, useCrossDerivatives, useCubicHermiteThroughWall)

        return annotationGroups

    @classmethod
    def generateMesh(cls, region, options):
        """
        Generate base or refined mesh.
        :param region: Zinc region to create mesh in. Must be empty.
        :param options: Dict containing options. See getDefaultOptions().
        """
        if not options['Refine']:
            return cls.generateBaseMesh(region, options)

        refineElementsCountAround = options['Refine number of elements around']
        refineElementsCountAlong = options['Refine number of elements along segment']
        refineElementsCountThroughWall = options['Refine number of elements through wall']

        baseRegion = region.createRegion()
        baseAnnotationGroups = cls.generateBaseMesh(baseRegion, options)

        meshrefinement = MeshRefinement(baseRegion, region, baseAnnotationGroups)
        meshrefinement.refineAllElementsCubeStandard3d(refineElementsCountAround, refineElementsCountAlong, refineElementsCountThroughWall)
        return meshrefinement.getAnnotationGroups()

class TubeMeshSegmentInnerPointsNoTeniaColi:
    """
    Generates a class object and function to pass the inner profile
    of the colon segment to tubemesh.
    """

    def __init__(self, region, elementsCountAroundMZ, elementsCountAroundNonMZ,
    elementsCountAlongSegment, segmentLength, wallThickness):

        self._region = region
        self._elementsCountAroundMZ = elementsCountAroundMZ
        self._elementsCountAroundNonMZ = elementsCountAroundNonMZ
        self._elementsCountAlongSegment = elementsCountAlongSegment
        self._segmentLength = segmentLength
        self._wallThickness = wallThickness

    def getTubeMeshSegmentInnerPoints(self, startRadius, startRadiusDerivative,
        endRadius, endRadiusDerivative, startMZWidth, startMZWidthDerivative,
        endMZWidth, endMZWidthDerivative):

        return getColonSegmentInnerPointsNoTeniaColi(self._region, self._elementsCountAroundMZ,
            self._elementsCountAroundNonMZ, self._elementsCountAlongSegment,
            self._segmentLength, self._wallThickness,
            startRadius, startRadiusDerivative, endRadius, endRadiusDerivative,
            startMZWidth, startMZWidthDerivative, endMZWidth, endMZWidthDerivative)

def getColonSegmentInnerPointsNoTeniaColi(region, elementsCountAroundMZ, elementsCountAroundNonMZ,
    elementsCountAlongSegment, segmentLength, wallThickness,
    startRadius, startRadiusDerivative, endRadius, endRadiusDerivative,
    startMZWidth, startMZWidthDerivative, endMZWidth, endMZWidthDerivative):
    """
    Generates a 3-D colon segment mesh with a simple mesentery
    (no tenia coli) with variable numbers of elements around,
    along the central line, and through wall. The colon segment
    has a cylindrical profile.
    :param elementsCountAroundMZ: Number of elements around mesenteric zone.
    :param elementsCountAroundNonMZ: Number of elements around non-mesenteric zone.
    :param elementsCountAlongSegment: Number of elements along colon segment.
    :param segmentLength: Length of a colon segment.
    :param wallThickness: Thickness of wall.
    :param startRadius: Inner radius at proximal end of colon segment.
    :param startRadiusDerivative: Rate of change of radius at proximal end.
    :param endRadius: Inner radius at distal end of colon segment.
    :param endRadiusDerivative: Rate of change of radius at distal end.
    :param startMZWidth: Width of mesenteric zone in proximal end.
    :param startMZWidthDerivative: Rate of change of mesenteric zone width
    on proximal end.
    :param endMZWidth: Width of mesenteric zone on distal end.
    :param endMZWidthDerivative: Rate of change of mesenteric zone width
    on distal end.
    :return annotationGroups, annotationArray: annotationArray stores annotation
    names of elements around
    :return transitElementList: stores true if element around is an element that
    transits from tenia coli / mesenteric zone to haustrum / non-mesenteric zone.
    :return uList: List of xi for node around
    :return coordinates, derivatives on inner surface of a colon segment.
    :return segmentAxis: Axis of segment
    :return sRadius: List of radius for each element along segment.
    :return sMZWidth: List of width of mesenteric zone for each element along segment.
    """

    mzGroup = AnnotationGroup(region, 'mesenteric zone', FMANumber = 'FMANumber unknown', lyphID = 'Lyph ID unknown')
    nonmzGroup = AnnotationGroup(region, 'non-mesenteric zone', FMANumber = 'FMANumber unknown', lyphID = 'Lyph ID unknown')
    annotationGroups = [mzGroup, nonmzGroup]
    annotationArray = ['mesenteric zone']*int(elementsCountAroundMZ*0.5) + ['non-mesenteric zone']*elementsCountAroundNonMZ + ['mesenteric zone']*int(elementsCountAroundMZ*0.5)
    transitElementList = [0]*int(elementsCountAroundMZ*0.5) + [1] + [0]*int(elementsCountAroundNonMZ - 2) + [1] + [0]*int(elementsCountAroundMZ*0.5)

    sRadius = []
    sMZWidth = []
    for n2 in range(elementsCountAlongSegment + 1):
        xi = 1/elementsCountAlongSegment * n2
        radius = interp.interpolateCubicHermite([startRadius], [startRadiusDerivative], [endRadius], [endRadiusDerivative], xi)[0]
        sRadius.append(radius)
        mzWidth = interp.interpolateCubicHermite([startMZWidth], [startMZWidthDerivative], [endMZWidth], [endMZWidthDerivative], xi)[0]
        sMZWidth.append(mzWidth)

    # create nodes
    x = [ 0.0, 0.0, 0.0 ]
    d1 = [ 0.0, 0.0, 0.0 ]
    sampleElementOut = 20
    segmentAxis = [0.0, 0.0, 1.0]
    elementsCountAround = elementsCountAroundMZ + elementsCountAroundNonMZ

    d2Raw = []
    xList = []
    d1List = []
    d2List = []

    uList = []
    lengthAroundFaceList = []

    for n2 in range(elementsCountAlongSegment + 1):
        z = segmentLength / elementsCountAlongSegment * n2
        x, d1 = createSegmentNoTeniaColi(elementsCountAroundMZ, elementsCountAroundNonMZ, sMZWidth[n2], sRadius[n2], sampleElementOut)
        d1List = d1List + d1
        xFace = []
        for n1 in range(elementsCountAround):
            xList.append([x[n1][0], x[n1][1], z])
            xFace.append([x[n1][0], x[n1][1], z])
        uFace, lengthAroundFace = getuListFromOuterLengthProfile(xFace, d1, segmentAxis, wallThickness, transitElementList)
        uList.append(uFace)
        lengthAroundFaceList.append(lengthAroundFace)

    for n1 in range(elementsCountAround):
        xUp = []
        d2Up = []
        for n2 in range(elementsCountAlongSegment + 1):
            n = elementsCountAround * n2 + n1
            xUp.append(xList[n])
            d2 = [ xList[n + elementsCountAround][i] - xList[n][i] if n2 < elementsCountAlongSegment else xList[n][i] - xList[n - elementsCountAround][i] for i in range(3)]
            d2Up.append(d2)
        d2Smoothed = interp.smoothCubicHermiteDerivativesLine(xUp, d2Up)
        d2Raw.append(d2Smoothed)

    # Re-arrange d2Raw
    for n2 in range(elementsCountAlongSegment + 1):
        for n1 in range(elementsCountAround):
            d2List.append(d2Raw[n1][n2])

    return annotationGroups, annotationArray, transitElementList, uList, lengthAroundFaceList, xList, d1List, d2List, segmentAxis, sRadius, sMZWidth

def createSegmentNoTeniaColi(elementsCountAroundMZ, elementsCountAroundNonMZ, mzWidth, radius, sampleElementOut):
    """
    Find locations and derivative of nodes in a cross-sectional profile
    of a colon segment with a simple mesentery.
    :param elementsCountAroundMZ: Number of elements around mesenteric zone.
    :param elementsCountAroundNonMZ: Number of elements around non-mesenteric zone.
    :param mzWidth: Width of mesenteric zone.
    :param radius: Inner radius of colon segment.
    :param sampleElementOut: Number of sample points used to set up profile
    :return: Node location and derivative of the cross-sectional profile of a segment.
    """

    xMZ = []
    d1MZ = []
    xList = []
    d1List = []
    xFaceProfile = []
    d1FaceProfile = []

    #Set up profile
    nx, nd1 = createCirclePoints([ 0.0, 0.0, 0.0 ], [ radius, 0.0, 0.0 ], [ 0.0, radius, 0.0 ], sampleElementOut, startRadians = 0.0)

    # Sample half mesenteric zone into equally spaced nodes
    radiansAroundMZ = 2*math.asin(mzWidth/(2*radius))
    radiansPerElementAroundMZ = radiansAroundMZ / elementsCountAroundMZ
    for n1 in range(int(elementsCountAroundMZ*0.5 + 1)):
        radiansAround = radiansPerElementAroundMZ * n1
        cosRadiansAround = math.cos(radiansAround)
        sinRadiansAround = math.sin(radiansAround)
        x = [ radius*cosRadiansAround,
              radius*sinRadiansAround,
              0.0 ]
        d1 = [ -radius*sinRadiansAround*radiansPerElementAroundMZ,
                radius*cosRadiansAround*radiansPerElementAroundMZ,
                0.0]
        xMZ.append(x)
        d1MZ.append(d1)
    arcLengthPerMZ = radius*radiansPerElementAroundMZ

    # Sample half non-mesenteric zone into equally spaced nodes
    halfCircumference = math.pi*radius
    xNonMZ, d1NonMZ, arcLengthPerNonMZ, arcLengthPerTransition = sampleHaustrum(nx, nd1, xMZ[-1], d1MZ[-1], halfCircumference, mzWidth*0.5, elementsCountAroundNonMZ)
    xFaceProfile = xList + xMZ + xNonMZ[1:]
    d1FaceProfile = d1List + d1MZ + d1NonMZ[1:]
    lengthHalfList = len(xFaceProfile)

    # Reflect to get other half
    for n in range(1,int(lengthHalfList)-1):
        idx =  -n + lengthHalfList - 1
        x = xFaceProfile[idx]
        d1 = d1FaceProfile[idx]
        xReflect = [x[0], -x[1], x[2]]
        d1Reflect = [-d1[0], d1[1], d1[2]]
        xFaceProfile.append(xReflect)
        d1FaceProfile.append(d1Reflect)

    return xFaceProfile, d1FaceProfile
