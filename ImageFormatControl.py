import os
import PySpin
import sys

import mqtt
import asyncio
from pathlib import Path
import httpcore

client = None

def configure_custom_image_settings(nodemap):
    try:
        node_pixel_format = PySpin.CEnumerationPtr(nodemap.GetNode('PixelFormat'))
        if PySpin.IsAvailable(node_pixel_format) and PySpin.IsWritable(node_pixel_format):

            # Retrieve the desired entry node from the enumeration node
            node_pixel_format_mono8 = PySpin.CEnumEntryPtr(node_pixel_format.GetEntryByName('BGR8')) # Mono8 BGR8
            if PySpin.IsAvailable(node_pixel_format_mono8) and PySpin.IsReadable(node_pixel_format_mono8):

                # Retrieve the integer value from the entry node
                pixel_format_mono8 = node_pixel_format_mono8.GetValue()

                # Set integer as new value for enumeration node
                node_pixel_format.SetIntValue(pixel_format_mono8)

                print('Pixel format set to %s...' % node_pixel_format.GetCurrentEntry().GetSymbolic())

            else:
                print('Pixel format mono 8 not available...')

        else:
            print('Pixel format not available...')

        # Apply minimum to offset X
        #
        # *** NOTES ***
        # Numeric nodes have both a minimum and maximum. A minimum is retrieved
        # with the method GetMin(). Sometimes it can be important to check
        # minimums to ensure that your desired value is within range.
        node_offset_x = PySpin.CIntegerPtr(nodemap.GetNode('OffsetX'))
        if PySpin.IsAvailable(node_offset_x) and PySpin.IsWritable(node_offset_x):

            node_offset_x.SetValue(node_offset_x.GetMin())
            print('Offset X set to %i...' % node_offset_x.GetMin())
            
        else:
            print('Offset X not available...')

        # Apply minimum to offset Y
        #
        # *** NOTES ***
        # It is often desirable to check the increment as well. The increment
        # is a number of which a desired value must be a multiple of. Certain
        # nodes, such as those corresponding to offsets X and Y, have an
        # increment of 1, which basically means that any value within range
        # is appropriate. The increment is retrieved with the method GetInc().
        node_offset_y = PySpin.CIntegerPtr(nodemap.GetNode('OffsetY'))
        if PySpin.IsAvailable(node_offset_y) and PySpin.IsWritable(node_offset_y):

            node_offset_y.SetValue(node_offset_y.GetMin())
            print('Offset Y set to %i...' % node_offset_y.GetMin())

        else:
            print('Offset Y not available...')

        # Set maximum width
        #
        # *** NOTES ***
        # Other nodes, such as those corresponding to image width and height,
        # might have an increment other than 1. In these cases, it can be
        # important to check that the desired value is a multiple of the
        # increment. However, as these values are being set to the maximum,
        # there is no reason to check against the increment.
        node_width = PySpin.CIntegerPtr(nodemap.GetNode('Width'))
        if PySpin.IsAvailable(node_width) and PySpin.IsWritable(node_width):

            width_to_set = node_width.GetMax()
            node_width.SetValue(width_to_set)
            print('Width set to %i...' % node_width.GetValue())
            
        else:
            print('Width not available...')

        # Set maximum height
        #
        # *** NOTES ***
        # A maximum is retrieved with the method GetMax(). A node's minimum and
        # maximum should always be a multiple of its increment.
        node_height = PySpin.CIntegerPtr(nodemap.GetNode('Height'))
        if PySpin.IsAvailable(node_height) and PySpin.IsWritable(node_height):

            height_to_set = node_height.GetMax()
            node_height.SetValue(height_to_set)
            print('Height set to %i...' % node_height.GetValue())

        else:
            print('Height not available...')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return True


def print_device_info(nodemap):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :type nodemap: INodeMap
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    print('*** DEVICE INFORMATION ***\n')

    try:
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not available.')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return True


def pre_acquire_images(nodemap):

    print('*** IMAGE ACQUISITION ***\n')
    try:
        handlingMode = PySpin.CEnumerationPtr(nodemap.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsAvailable(handlingMode) or not PySpin.IsWritable(handlingMode):
            print('Unable to set Buffer Handling mode (node retrieval). Aborting...\n')
        else:
            handlingModeNewFirst = PySpin.CEnumEntryPtr(handlingMode.GetEntryByName('OldestFirst'))
            if not PySpin.IsAvailable(handlingModeNewFirst) or not PySpin.IsReadable(handlingModeNewFirst):
                print('Unable to set Buffer Handling mode (Value retrieval). Aborting...\n')
            else:
                handlingMode.SetIntValue(handlingModeNewFirst.GetValue())
                print('Buffer Handling Mode set to OldestFirst...')

        nodeAcquisitionFramerate = PySpin.CFloatPtr(nodemap.GetNode("AcquisitionFrameRate"))
        if not PySpin.IsAvailable(nodeAcquisitionFramerate) and not PySpin.IsReadable(nodeAcquisitionFramerate):
            print('Unable to retrieve frame rate. Aborting...')
        else:
            nodeAcquisitionFramerate.SetValue(1)


        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        print('Acquisition mode set to continuous...')

        '''
        cam.BeginAcquisition()

        print('Acquiring images...')

        device_serial_number = ''
        node_device_serial_number = PySpin.CStringPtr(nodemap_tldevice.GetNode('DeviceSerialNumber'))
        if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
            device_serial_number = node_device_serial_number.GetValue()
            print('Device serial number retrieved as %s...' % device_serial_number)
        '''
    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False
    return True

system, cam_list, cam, stopFlag, quitFlag = None, None, None, None, None

async def stop_acquired(cam):
    global stopFlag
    while True:
        await asyncio.sleep(0.1)
        if stopFlag == True:
            break
    cam.EndAcquisition()

async def acquire_images(cam):
    global client, stopFlag
    for i in range(1024 * 1024):
        await asyncio.sleep(0.1)
        if stopFlag == True:
            return
        try:
            image_result = cam.GetNextImage(1000)
            #if acquire_continue_flag:
            #    continue
            #acquire_continue_flag = True

            if image_result.IsIncomplete():
                print('Image incomplete with image status %d ...' % image_result.GetImageStatus())

            elif i % 4 == 0:
                print(fr'이미지 취득 ({i}), width = {image_result.GetWidth()}, height = {image_result.GetHeight()}')

                #image_result = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)


                image_result.Save(fr'{Path.home()}/Pictures/cam.jpg')
                image_result.Release()
                mqtt.publish(client, '/img-save-ready')
                print('PUB', '/img-save-ready')


        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
        mqtt.publish(client, '/img-save-ready')
    stopFlag = True

def run_single_camera(cam):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam: Camera to run on.
    :type cam: CameraPtr
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        #nodemap_tldevice = cam.GetTLDeviceNodeMap()
        cam.Init()

        nodemap = cam.GetNodeMap()

        if not configure_custom_image_settings(nodemap):
            return False

        # 카메라 이미지 취득 준비
        pre_acquire_images(nodemap)


    except PySpin.SpinnakerException as ex:
        print(fr'에러:\r\n{ex}')
    return True

def main():
    """
    Example entry point; please see Enumeration example for more in-depth
    comments on preparing and cleaning up the system.

    :return: True if successful, False otherwise.
    :rtype: bool
    """

    # 현재 프로세스의 파일 쓰기 권한 확인
    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return None, None

    test_file.close()
    os.remove(test_file.name)
    ##

    # 현재 라이브러리 버전 확인
    #version = system.GetLibraryVersion()
    #print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # 싱글톤 시스템 객체 취득- 시작점
    system = PySpin.System.GetInstance()


    # 카메라 리스트 반환
    cam_list = system.GetCameras()

    # 카메라가 없는 경우
    if cam_list.GetSize() == 0:
        cam_list.Clear()
        system.ReleaseInstance()

        print('카메라가 없습니다.')
        input('아무 키나 누르세요...')
        return None, None
    return system, cam_list



async def mqtt_main():
    global client, stopFlag, quitFlag, cam, system
    while True:
        await asyncio.sleep(3)

        res = httpcore.request("GET", "http://localhost:8888/is-grab")
        if res.status == 200:
            pass
        elif res.status == 400:
            if run_single_camera(cam) == True:
                stopFlag = False
                print("카메라 이미지 취득 시작")
                cam.BeginAcquisition()
                mqtt.publish(client, '/img-start-ready')
                asyncio.gather(acquire_images(cam), stop_acquired(cam))
        elif res.status == 401:
            print("취득 종료")
            stopFlag = True
        elif res.status == 404:
            print("카메라 객체 반환")
            try:
                cam.EndAcquisition()
            except Exception as e:
                print('cam.EndAcquisition()', e.message)
                pass
            try:
                cam.DeInit()
            except Exception as e:
                print('cam.DeInit()', e.message)
                pass
            del cam
            cam_list.Clear()
            system.ReleaseInstance()
            sys.exit(0)


if __name__ == '__main__':
    #MQTT
    client = mqtt.newConnection()

    system, cam_list = main()

    if cam_list:
        cam = cam_list.GetByIndex(0)
        if not cam:
            sys.exit(0)
    else:
        sys.exit(0)
    asyncio.get_event_loop().run_until_complete(mqtt_main())