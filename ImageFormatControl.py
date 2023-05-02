import torchvision.transforms.functional as F
from PIL import Image, ImageEnhance
import PySpin
import sys
import zmq
import pickle
from reactivex import Subject
from pathlib import Path
import base64
from io import BytesIO

client = None

# 0MQ
context = zmq.Context()
socket = context.socket(zmq.PULL)
socket.connect("tcp://127.0.0.1:1881")
print("Connected to 0MQ Server - PULL.")
socketPush = context.socket(zmq.PUSH)
socketPush.bind("tcp://127.0.0.1:1880")
print("bound to 0MQ Server - PUSH.")
# 0MQ End.

import os, os.path
import time

def configure_custom_image_settings(nodemap, s_nodemap):
    try:
        def setNodeValue(nodeName, nodeValue):
            node = None
            if nodeValue == True or nodeValue == False:
                node = PySpin.CBooleanPtr(nodemap.GetNode(nodeName))
            elif isinstance(nodeValue, int) or isinstance(nodeValue, str):
                node = PySpin.CEnumerationPtr(nodemap.GetNode(nodeName))
            elif isinstance(nodeValue, float):
                node = PySpin.CFloatPtr(nodemap.GetNode(nodeName))
            else:
                return False
            if node is None:
                print("노드 값 데이터형을 지원하지 않음")
                return False
            if not PySpin.IsAvailable(node):
                print("노드가 가능하지 않음.")
                return False
            if  not PySpin.IsWritable(node):
                print("노드에 쓸 수 없음.")
                return False
            if isinstance(nodeValue, str):
                handlingNodeValue = PySpin.CEnumEntryPtr(node.GetEntryByName(nodeValue))
                if not PySpin.IsAvailable(handlingNodeValue) or not PySpin.IsReadable(handlingNodeValue):
                    return False
                handlingNodeValue = handlingNodeValue.GetValue()
            else:
                handlingNodeValue = nodeValue
            print(f'{nodeName} = {handlingNodeValue} {type(handlingNodeValue)} 설정 시도...')
            if handlingNodeValue is not None:
                if nodeValue == True or nodeValue == False:
                    node.SetValue(handlingNodeValue)
                elif isinstance(nodeValue, int) or isinstance(nodeValue, str):
                    node.SetIntValue(handlingNodeValue)
                else: #Float 형
                    node.SetValue(handlingNodeValue)
                return True
            return False
        if not setNodeValue('AcquisitionMode', 'Continuous'): # SingleFrame, MultiFrame, Continuous 중 하나
            print('AcquisitionMode=Continuous 설정 실패')
        if not setNodeValue('AcquisitionFrameRateEnable', True):
            print('AcquisitionFrameRateEnable=True 설정 실패')
        if not setNodeValue('AcquisitionFrameRate', 18.0):
            print('AcquisitionFrameRate=1.0 설정 실패')
        if not setNodeValue('TriggerMode', 'On'):
            print('TriggerMode 설정 실패')
        if not setNodeValue('TriggerSource', 'Software'):
            print('TriggerSource 설정 실패')
        if not setNodeValue('TriggerSelector', 'FrameStart'): #AcquisitionStart
            print('TriggerSelector 설정 실패')



        # Set  Buffer Handling Mode to OldestFirst
        handlingMode = PySpin.CEnumerationPtr(s_nodemap.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsAvailable(handlingMode) or not PySpin.IsWritable(handlingMode):
            print('Unable to set Buffer Handling mode (node retrieval). Aborting...\n')
            return False

        handlingModeEntry = PySpin.CEnumEntryPtr(handlingMode.GetCurrentEntry())
        if not PySpin.IsAvailable(handlingModeEntry) or not PySpin.IsReadable(handlingModeEntry):
            print('Unable to set Buffer Handling mode (Entry retrieval). Aborting...\n')
            return False

        handlingModeNewestOnly = PySpin.CEnumEntryPtr(handlingMode.GetEntryByName('OldestFirst')) #NewestFirst OldestFirst
        if not PySpin.IsAvailable(handlingModeNewestOnly) or not PySpin.IsReadable(handlingModeNewestOnly):
            print('Unable to set Buffer Handling mode (Value retrieval). Aborting...\n')
            return False

        handlingMode.SetIntValue(handlingModeNewestOnly.GetValue())
        print('Buffer Handling Mode set to NewestFirst...')
        # Set stream buffer Count Mode to manual
        stream_buffer_count_mode = PySpin.CEnumerationPtr(s_nodemap.GetNode('StreamBufferCountMode'))
        if not PySpin.IsAvailable(stream_buffer_count_mode) or not PySpin.IsWritable(stream_buffer_count_mode):
            print('Unable to set Buffer Count Mode (node retrieval). Aborting...\n')
            return False

        stream_buffer_count_mode_manual = PySpin.CEnumEntryPtr(stream_buffer_count_mode.GetEntryByName('Manual'))
        if not PySpin.IsAvailable(stream_buffer_count_mode_manual) or not PySpin.IsReadable(stream_buffer_count_mode_manual):
            print('Unable to set Buffer Count Mode entry (Entry retrieval). Aborting...\n')
            return False

        stream_buffer_count_mode.SetIntValue(stream_buffer_count_mode_manual.GetValue())
        print('Stream Buffer Count Mode set to manual...')

        # Retrieve and modify Stream Buffer Count
        buffer_count = PySpin.CIntegerPtr(s_nodemap.GetNode('StreamBufferCountManual'))
        if not PySpin.IsAvailable(buffer_count) or not PySpin.IsWritable(buffer_count):
            print('Unable to set Buffer Count (Integer node retrieval). Aborting...\n')
            return False

        # Display Buffer Info
        print('Default Buffer Count: %d' % buffer_count.GetValue())
        print('Maximum Buffer Count: %d' % buffer_count.GetMax())
        buffer_count.SetValue(20)
        print('Buffer count now set to: %d' % buffer_count.GetValue())

        ''' 싱글프레임모드일 경우 제외
        nodeAcquisitionFramerate = PySpin.CFloatPtr(nodemap.GetNode("AcquisitionFrameRate"))
        if not PySpin.IsAvailable(nodeAcquisitionFramerate) and not PySpin.IsReadable(nodeAcquisitionFramerate):
            print('Unable to retrieve frame rate. Aborting...')
        else:
            nodeAcquisitionFramerate.SetValue(5.0)
        '''

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

system, cam_list, cam, quitFlag, acquisitonCount = None, None, None, None, -1

def triggerSet(cam):
    # Execute software trigger
    try:
        nodemap = cam.GetNodeMap()
        node_softwaretrigger_cmd = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
        if not PySpin.IsAvailable(node_softwaretrigger_cmd) or not PySpin.IsWritable(node_softwaretrigger_cmd):
            print('Unable to execute trigger. Aborting...')
            return False
        node_softwaretrigger_cmd.Execute()
    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
    ###


def acquire_images(image_result, count, isSaved):
    global client
    try:
        if isSaved == False:
            image_result.Release()
            return

        if image_result.IsIncomplete():
            print('Image incomplete with image status %d ...' % image_result.GetImageStatus())
        else:

            image_result = image_result.Convert(PySpin.PixelFormat_BGR8, PySpin.IIDC) #IIDC
            #image_result_0 = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.IIDC)
            im = Image.fromarray(image_result.GetNDArray())
            im = im.resize((480, 320)) # 3:2 HVGA
            im = F.adjust_hue(im, -166 / 180 * 0.5)
            #im = F.adjust_hue(im, -169 / 180 * 0.5)
            #im = F.adjust_saturation(im, 1.5)
            #im = ImageEnhance.Contrast(im).enhance(1.5)
            buffered = BytesIO()
            im.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue())
            socketPush.send_multipart(msg_parts=["raw-img", img_str], copy=False, track=False)
            print(fr'0MQ 전송 완료')

            image_result.Save(fr'{Path.home()}/Pictures/cam.jpg')
            print(fr'이미지 저장 완료, width = {image_result.GetWidth()}, height = {image_result.GetHeight()} ({image_result.GetFrameID()})')

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        #traceback.print_exc()

class ImageEventHandler(PySpin.ImageEventHandler):
    def __init__(self, cam):
        super(ImageEventHandler, self).__init__()

    def OnImageEvent(self, image):
        global acquisitonCount
        acquisitonCount = acquisitonCount + 1
        acquire_images(image, acquisitonCount, True)

eventHandler = ImageEventHandler(cam)
def run_single_camera(cam):
    global eventHandler
    try:
        #nodemap_tldevice = cam.GetTLDeviceNodeMap()
        cam.Init()
        nodemap = cam.GetNodeMap()
        s_nodemap = cam.GetTLStreamNodeMap()

        if not configure_custom_image_settings(nodemap, s_nodemap):
            return False

        # 카메라 이미지 취득 준비
        # pre_acquire_images(nodemap)
        cam.RegisterEventHandler(eventHandler)


    except PySpin.SpinnakerException as ex:
        print(fr'에러:\r\n{ex}')
        return False
    return True

def main():
    # 현재 프로세스의 파일 쓰기 권한 확인
    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return None, None

    test_file.close()
    os.remove(test_file.name)

    # 현재 라이브러리 버전 확인
    #version = system.GetLibraryVersion()
    #print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # 싱글톤 시스템 객체 취득 - 시작점
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


def init_cam():
    global cam_list, cam, system
    if run_single_camera(cam) == False:
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
        exit(0)
    else:
        print("카메라 이미지 취득 시작")
        print(f'cam={cam}')
        cam.BeginAcquisition()

def open_0mq():
    global cam_list, cam, system

    subject = Subject()
    def subscribeSocket(result):
        (connectionCount, status, msg) = result
        print(f'status={status}, msg={msg} ({connectionCount})')

        if status == 200:  # 정상
            pass
        elif status == 401:  # 중지
            pass
        elif status == 400:  # 소프트웨어 트리거
            print("트리거")
            triggerSet(cam)
    subscription = subject.subscribe(subscribeSocket)

    connectionCount = 0
    while True:
        try:
            #await asyncio.sleep(0.11) 간헐적 응답 실패 이유로 주석 처리됨.
            result = socket.recv_string() # 블록됨.
            connectionCount = connectionCount + 1
            status, msg = result.split()
            status = int(status)

            # 프로그램 종료
            if status == 402:
                subscription.dispose()
                print("카메라 객체 반환")
                try:
                    cam.EndAcquisition()
                except Exception as e:
                    print('cam.EndAcquisition()', e.message)
                    pass
                try:
                    cam.UnregisterEventHandler(eventHandler)
                    cam.DeInit()
                except Exception as e:
                    print('cam.DeInit()~', e.message)
                    pass
                del cam
                cam_list.Clear()
                system.ReleaseInstance()
                print("잠시후 프로그램이 종료됩니다.")
                break
            else:
                subject.on_next((connectionCount, status, msg))
        except ConnectionRefusedError:
            print('ConnectionRefusedError')
            #await asyncio.sleep(3)
            pass
        except:
            pass

if __name__ == '__main__':
    system, cam_list = main()

    if cam_list:
        cam = cam_list.GetByIndex(0)
        if not cam:
            sys.exit(0)
        init_cam()
        open_0mq()