import threading

import PySpin
import time
import base64
import json
import atexit
import ctypes
import traceback
from reactivex import Subject
from PIL import Image
from io import BytesIO
from os import remove
from pathlib import Path
from STOMPClient import MQ
from CameraAction.inital.CameraAction import *
from CameraAction.inital.CameraSetting import *

flir = None
grabTime = 0
class Arguements():
    X1 = None
    Y1 = None
    X2 = None
    Y2 = None
    X1_0 = None
    Y1_0 = None
    X2_0 = None
    Y2_0 = None
    X1_1 = None
    Y1_1 = None
    X2_1 = None
    Y2_1 = None
    X1_2 = None
    Y1_2 = None
    X2_2 = None
    Y2_2 = None
    Angle = None
    Angle_0 = None
    Angle_1 = None
    Angle_2 = None

arguments = Arguements()

class FLIRCameraSetting(CameraSetting):
    s_nodemap = None
    nodemap = None
    def setStreamNodeMap(self, s_nodemap):
        self.s_nodemap = s_nodemap
    def setNodeMap(self, nodemap):
        self.nodemap = nodemap

    def setNodeValue(self, nodeName, nodeValue):
        if nodeValue == True or nodeValue == False:
            node = PySpin.CBooleanPtr(self.nodemap.GetNode(nodeName))
        elif isinstance(nodeValue, int) or isinstance(nodeValue, str):
            node = PySpin.CEnumerationPtr(self.nodemap.GetNode(nodeName))
        elif isinstance(nodeValue, float):
            node = PySpin.CFloatPtr(self.nodemap.GetNode(nodeName))
        else:
            return False
        if node is None:
            print("노드 값 데이터형을 지원하지 않음")
            return False
        if not PySpin.IsAvailable(node):
            print("노드가 가능하지 않음.")
            return False
        if not PySpin.IsWritable(node):
            print("노드에 쓸 수 없음.")
            return False
        if isinstance(nodeValue, str):
            handlingNodeValue = PySpin.CEnumEntryPtr(node.GetEntryByName(nodeValue))
            if not PySpin.IsAvailable(handlingNodeValue) or not PySpin.IsReadable(handlingNodeValue):
                return False
            handlingNodeValue = handlingNodeValue.GetValue()
        else:
            handlingNodeValue = nodeValue
        print(f'{nodeName} = {handlingNodeValue} {type(handlingNodeValue)}')
        if handlingNodeValue is not None:
            if nodeValue == True or nodeValue == False:
                node.SetValue(handlingNodeValue)
            elif isinstance(nodeValue, int) or isinstance(nodeValue, str):
                node.SetIntValue(handlingNodeValue)
            else:  # Float 형
                node.SetValue(handlingNodeValue)
            print(f'INFO FLIRCameraSetting > setNodeValue: {nodeName} = {handlingNodeValue} {type(handlingNodeValue)} 설정 성공.')
            return True
        print(f'ERROR FLIRCameraSetting > setNodeValue: {nodeName} = {handlingNodeValue} {type(handlingNodeValue)} 설정 실패!')
        return False

    def IsNodeAvailable(self, node, option="arw"):
        if option in 'a' and not PySpin.IsAvailable(node):
            return False
        if option in 'r' and not PySpin.IsReadable(node):
            return False
        if option in 'w' and not PySpin.IsWritable(node):
            return False
        return True

acquisitonCount = 0
class ImageEventHandler(PySpin.ImageEventHandler):
    def __init__(self):
        super(ImageEventHandler, self).__init__()

    def OnImageEvent(self, image):
        global acquisitonCount, flir
        acquisitonCount = acquisitonCount + 1
        flir.onGrab(flir.currentCamIndex, image, acquisitonCount, True)
class cameraMQ():
    def setArgumentsFromJsonString(self, value):
        global arguments
        payload = json.loads(value)
        for (key, value) in payload.items():
            if isinstance(value, int):
                arguments.__setattr__(key, int(value))
            else:
                arguments.__setattr__(key, value)

        print("Arguments set.")
    #subject = Subject()

    messageCallback = None
    subject = None
    subscription = None

    def onCreated(self, onInit):
        self.subject = Subject()
        self.subscription = self.subject.subscribe(self.onMessage)
        MQ.addSubject(self.onMessage)
        MQ.setTopicList(['/img-stop', '/cam-release', '/img-start', '/img-start-0', '/img-start-1', '/img-start-2',
                         '/on-change-param', '/q'])
        MQ.init(onInit=onInit)

    def defineMessageCallback(self, onMessageCallback):
        self.messageCallback = onMessageCallback

    def onMessage(self, payload):
        (topic, message) = payload
        print(f'STOMP: topic={topic}, msg={message}')
        self.messageCallback(topic, message)

class FLIRCameraAction(CameraAction):
    system = None
    cam_list = None
    currentCamIndex = None
    eventHandler = None
    mq = cameraMQ()
    cameraSetting = FLIRCameraSetting()
    VENDER_TYPE = 'FLIR'

    errorTag = "ERROR FLIRCameraAction > onMounted:"
    infoTag = "INFO FLIRCameraAction > onMounted:"

    def initSystemAndCameraList(self):
        # 현재 프로세스의 파일 쓰기 권한 확인
        try:
            test_file = open('test.txt', 'w+')
        except IOError:
            print('Unable to write to current directory. Please check permissions.')
            input('Press Enter to exit...')
            return False

        test_file.close()
        remove(test_file.name)

        # 현재 라이브러리 버전 확인
        # version = system.GetLibraryVersion()
        # print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

        # 싱글톤 시스템 객체 취득 - 시작점
        self.system = PySpin.System.GetInstance()

        # 카메라 리스트 반환
        self.cam_list = self.system.GetCameras()

        # 카메라가 없는 경우
        if self.cam_list.GetSize() == 0:
            self.cam_list.Clear()
            self.system.ReleaseInstance()

            print('카메라가 없습니다.')
            input('아무 키나 누르세요...')
            return False
        return True

    def __init__(self):
        self.eventHandler = ImageEventHandler()
        def callback(topic, message):
            if topic == '':  # 정상
                print(f"STOMP: 토픽 값이 없습니다.")
                pass
            elif topic == '/img-stop':  # 중지
                print(f"STOMP: 이미지 취득을 중지합니다. (행위 없음)")
                MQ.pub('/cam-status', {'camNo': '-', 'type': self.VENDER_TYPE, 'status': 'Stopped'})
                pass
            elif topic == '/img-path':  # 이미지 저장 위치 변경 (수정 필요)
                print('이미지 경로 변경: ', message)
                # 파일 경로 유효성 검사
                isFilenameChanged = False
                if message.endsWith('/'):
                    try:
                        file = open(fr"{message}from-vision-software.txt", "w")
                        file.close()
                        imageBaseFilename = message
                        isFilenameChanged = True
                    except Exception:
                        pass
                elif message == "[My Pictures]":
                    imageBaseFilename = fr"{Path.home()}/Pictures/FLIR/"
                    isFilenameChanged = True

                if isFilenameChanged:
                    MQ.pub('/cam-status', {'camNo': '0', 'type': self.VENDER_TYPE, 'status': '이미지 저장 위치가 변경되었습니다.'})
                else:
                    MQ.pub('/cam-status',
                           {'camNo': '0', 'type': self.VENDER_TYPE, 'status': '이미지 저장 위치 변경 실패: 올바르지 않은 파일 위치 경로 에러'})
            elif topic == '/img-start-0' or topic == '/img-start':  # 소프트웨어 트리거
                if len(self.cam_list) >= 1:
                    print(f"STOMP: 소프트웨어 트리거 명령을 감지하였습니다.")
                    print("ReactiveX: 소프트웨어 트리거 ON. cam[0] /img-start-0")
                    self.currentCamIndex = 0
                    self.trigger(self.cam_list.GetByIndex(0))
            elif topic == '/img-start-1':  # 소프트웨어 트리거
                if len(self.cam_list) >= 2:
                    print(f"STOMP: 소프트웨어 트리거 명령을 감지하였습니다.")
                    print("ReactiveX: 소프트웨어 트리거 ON. cam[1] /img-start-1")
                    self.currentCamIndex = 1
                    self.trigger(self.cam_list.GetByIndex(1))
            elif topic == '/img-start-2':  # 소프트웨어 트리거
                if len(self.cam_list) >= 3:
                    print(f"STOMP: 소프트웨어 트리거 명령을 감지하였습니다.")
                    print("ReactiveX: 소프트웨어 트리거 ON. cam[2] /img-start-2")
                    self.currentCamIndex = 2
                    self.trigger(self.cam_list.GetByIndex(2))
            elif topic == '/img-start':  # 소프트웨어 트리거
                print(f"STOMP: 소프트웨어 트리거 명령을 감지하였습니다.")
                print("ReactiveX: 소프트웨어 트리거 ON. cam[0] /img-start")
                self.trigger(self.cam_list.GetByIndex(0))
            elif topic == '/good-0' or topic == '/bad-0' or topic == '/bg-0':
                pass
            elif topic == '/good-1' or topic == '/bad-1' or topic == '/bg-1':
                pass
            elif topic == '/good-2' or topic == '/bad-2' or topic == '/bg-2':
                pass
            elif topic == '/cam-release' or topic == '/q':
                self.release()
                exit(0)
            # Patching
            elif topic == '/on-good-0':
                TIME_SLEEP = 2.5
                print("/on-good-0")
            elif topic == '/on-change-param':
                self.mq.setArgumentsFromJsonString(message)
        self.mq.defineMessageCallback(callback)

        def initCamera():
            if self.initSystemAndCameraList():
                for index in range(self.cam_list.GetSize()):
                    cam = self.cam_list.GetByIndex(index=index)
                    cam.Init()
                    if not self.onMounted(cam):
                        self.release()
                        return
                self.onBeginAcquisition()
        self.mq.onCreated(initCamera)

    def onMounted(self, cam):
        self.cameraSetting.setStreamNodeMap(cam.GetTLStreamNodeMap())
        self.cameraSetting.setNodeMap(cam.GetNodeMap())
        try:
            # Set Buffer Handling Mode to OldestFirst
            handlingMode = PySpin.CEnumerationPtr(self.cameraSetting.s_nodemap.GetNode('StreamBufferHandlingMode'))
            if not self.cameraSetting.IsNodeAvailable(handlingMode, 'aw'):
                print(f'{self.errorTag} StreamBufferHandlingMode 값에 접근하고 쓰기 연산을 할 수 없습니다.')
                return False
            handlingModeEntry = PySpin.CEnumEntryPtr(handlingMode.GetCurrentEntry())
            if not self.cameraSetting.IsNodeAvailable(handlingModeEntry, 'ar'):
                print(f'{self.errorTag} StreamBufferHandlingMode 값에 접근하고 읽기 연산을 할 수 없습니다.')
                return False
            handlingModeNewestOnly = PySpin.CEnumEntryPtr(
                handlingMode.GetEntryByName('NewestFirst'))  # NewestFirst OldestFirst
            if not self.cameraSetting.IsNodeAvailable(handlingModeNewestOnly, 'ar'):
                print(f'{self.errorTag} NewestFirst 값에 접근하고 읽기 연산을 할 수 없습니다.')
                return False

            handlingMode.SetIntValue(handlingModeNewestOnly.GetValue())
            print(f'{self.infoTag} Buffer Handling Mode는 NewestFirst로 세트되었습니다.')

            # Set stream buffer Count Mode to manual
            bufferCountMode = PySpin.CEnumerationPtr(self.cameraSetting.s_nodemap.GetNode('StreamBufferCountMode'))
            if not self.cameraSetting.IsNodeAvailable(bufferCountMode, 'aw'):
                print(f'{self.errorTag} StreamBufferCountMode 값에 접근하고 쓰기 연산을 할 수 없습니다.')
                return False

            manual = PySpin.CEnumEntryPtr(bufferCountMode.GetEntryByName('Manual'))
            if not self.cameraSetting.IsNodeAvailable(manual, 'ar'):
                print(f'{self.errorTag} StreamBufferCountMode(Manual) 값에 접근하고 읽기 연산을 할 수 없습니다.')
                return False

            bufferCountMode.SetIntValue(manual.GetValue())
            print(f'{self.infoTag} Stream Buffer Count Mode는 Manual로 세트되었습니다.')

            # Retrieve and modify Stream Buffer Count
            buffer_count = PySpin.CIntegerPtr(self.cameraSetting.s_nodemap.GetNode('StreamBufferCountManual'))
            if not self.cameraSetting.IsNodeAvailable(buffer_count, 'aw'):
                print('Buffer Count를 세트하기 위해 StreamBufferCountManual에 접근하고 쓰기 연산할 수 없습니다.')
                return False

            self.cameraSetting.setNodeValue('AcquisitionMode', 'SingleFrame')  # SingleFrame, MultiFrame, Continuous 중 하나
            self.cameraSetting.setNodeValue('AcquisitionFrameRateEnable', True)
            self.cameraSetting.setNodeValue('AcquisitionFrameRate', 5.0)
            self.cameraSetting.setNodeValue('TriggerMode', 'Off')

            print("=========")
            print(" SUMMARY ")
            print("=========")
            # Display Buffer Info
            print('Default Buffer Count: %d' % buffer_count.GetValue())
            print('Maximum Buffer Count: %d' % buffer_count.GetMax())
            # buffer_count.SetValue(20)
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
            node_offset_x = PySpin.CIntegerPtr(self.cameraSetting.nodemap.GetNode('OffsetX'))
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
            node_offset_y = PySpin.CIntegerPtr(self.cameraSetting.nodemap.GetNode('OffsetY'))
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
            node_width = PySpin.CIntegerPtr(self.cameraSetting.nodemap.GetNode('Width'))
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
            node_height = PySpin.CIntegerPtr(self.cameraSetting.nodemap.GetNode('Height'))
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

    def print_device_info(self, nodemap):
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

    def trigger(self, cam):
        # Execute software trigger
        try:
            nodemap = self.cam_list.GetByIndex(0).GetNodeMap()
            triggerSoftware = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
            if not PySpin.IsAvailable(triggerSoftware) or not PySpin.IsWritable(triggerSoftware):
                print(f'{self.errorTag} Unable to execute trigger. Aborting...')
                return False
            #MQ.pub('/cam-status', {'camNo': '0', 'type': VENDER_TYPE, 'status': f'Trigger Start {time.time()}'})
            triggerSoftware.Execute()
            print("triggerSoftware.Execute()")
        except PySpin.SpinnakerException as ex:
            print(f'{self.errorTag} %s' % ex)

    def onGrab(self, camIndex, imagePtr, count, isSaved):
        global arguments
        """
        FLIR 머신비전 카메라 소프트웨어 트리거 콜백 함수
        :param image_result: 취득 이미지 객체
        :param count: 취득 이미지 일련번호 카운팅
        :param isSaved: 저장 여부, False일 경우 즉시 리턴.
        :return:
        """
        try:
            if isSaved == False:
                imagePtr.Release()
                return

            if imagePtr.IsIncomplete():
                print(f'{self.errorTag} Image incomplete with image status %d ...' % image_result.GetImageStatus())
                imagePtr.Release()
                return


            # ndarray = np.flip(image_converted.GetNDArray(), axis=2) # No Gamma Adjustment needed. only this applied.
            x1 = 0
            y1 = 0
            x2 = 0
            y2 = 0
            if arguments.X1 is not None:
                [x1, y1, x2, y2] = [arguments.X1, arguments.Y1, arguments.X2, arguments.Y2]
            elif arguments.X1_0 is not None:
                [x1, y1, x2, y2] = [arguments.X1_0, arguments.Y1_0, arguments.X2_0, arguments.Y2_0]
            else:
                print("onGrab return")
                return
            w = x2 - x1
            h = y2 - y1
            imagePtr = imagePtr.Convert(PySpin.PixelFormat_RGB8, PySpin.IIDC)
            imagePtr.ResetImage(w, h, x1, y1, PySpin.PixelFormat_RGB8)
            im = Image.fromarray(imagePtr.GetNDArray())
            # im = im.resize((480, 320)) # 3:2 HVGA
            # im = F.adjust_gamma(im, 0.5, 1)
            # im = F.adjust_hue(im, -166 / 180 * 0.5)
            # im = F.adjust_saturation(im, 1.5)
            # im = ImageEnhance.Contrast(im).enhance(1.5)
            buffered = BytesIO()
            im.save(buffered, format="JPEG")
            base64string = base64.b64encode(buffered.getvalue())
            message = f"Cam-No: {camIndex}\n" + \
                      f"Base64-0: {base64string.decode('ascii')}\n" + \
                      f"Time: {grabTime}"

            MQ.pub('/img-recv', message, 1)
            MQ.pub('/cam-status', {'camNo': camIndex, 'type': self.VENDER_TYPE,
                                   'status': f'Captured Image Sent. Origin ({imagePtr.GetWidth()}px, {imagePtr.GetHeight()}px)'})

            print(fr'전송 완료 FLIR ---> DNN')

            imagePtr.Save(fr'{Path.home()}/Pictures/FLIR/cam-{time.time()}.jpg')
            # MQ.pub('/cam-status', {'camNo': '0', 'type': VENDER_TYPE, 'status': 'Captured Image Saved'})
            print(
                fr'이미지 저장 완료, width = {imagePtr.GetWidth()}, height = {imagePtr.GetHeight()} ({imagePtr.GetFrameID()})')
            # socket['dnn-push'].send_multipart(msg_parts=['/start'.encode('utf8'), 'img_str'.encode('utf8')], copy=False, track=False)

        except PySpin.SpinnakerException as ex:
            MQ.pub('/cam-status', {'camNo': '0', 'type': self.VENDER_TYPE, 'status': ex})
            print('Error: %s' % ex)
        except Exception as ex:
            print('Error: %s' % ex)

    def onBeginAcquisition(self):
        for index in range(self.cam_list.GetSize()):
            cam = self.cam_list.GetByIndex(index=index)
            cam.BeginAcquisition()
            print(f"3 초간 촬영 테스트 후 이미지 취득을 시작합니다.")
            time.sleep(3)
            cam.EndAcquisition()
            self.cameraSetting.setNodeValue('TriggerMode', 'On')
            self.cameraSetting.setNodeValue('TriggerSource', 'Software')
            self.cameraSetting.setNodeValue('TriggerSelector', 'FrameStart')  # AcquisitionStart
            cam.RegisterEventHandler(self.eventHandler)
            cam.BeginAcquisition()
            print(f"이미지 취득을 시작합니다.")

    def release(self):
        print("ReactiveX: 구독을 종료합니다.")
        print("STOMP: 메시지 큐를 중지합니다.")
        print("STOMP: 카메라 객체를 반환합니다.")
        try:
            if not self.cameraSetting.setNodeValue('TriggerMode', 'Off'):
                MQ.pub('/cam-status', {'camNo': '0', 'type': self.VENDER_TYPE,
                                       'status': 'TriggerMode OFF 값 설정에 실패하였습니다. 뷰어를 통해 세팅 값을 초기화하시기 바랍니다.'})
                print('STOMP: TriggerMode OFF 값 설정에 실패하였습니다. 뷰어를 통해 세팅 값을 초기화하시기 바랍니다.')
            for index, cam in enumerate(self.cam_list):
                cam.EndAcquisition()
                cam.UnregisterEventHandler(self.eventHandler)
        except Exception as e:
            print('STOMP: cam.EndAcquisition()', e)
            pass
        try:
            for index, cam in enumerate(self.cam_list):
                cam.DeInit()
        except Exception as e:
            print('STOMP: cam.DeInit()', e)
            pass
        for index in range(len(self.cam_list)):
            cam = self.cam_list.GetByIndex(index)  # 메모리 자원 해제에 반드시 필요.
            del cam
        self.cam_list.Clear()
        self.system.ReleaseInstance()
        print('STOMP: 메시지 큐 클라이언트를 종료합니다.')
        if self.mq.subscription is not None:
            self.mq.subscription.dispose()
        MQ.stop()

# 진입점
flir = FLIRCameraAction()

#daemon2 = threading.Thread(target=fn2, args=())
#daemon2.setDaemon(True)
#daemon2.start()

exitFlag = True
try:
    while exitFlag:
        time.sleep(1)
except KeyboardInterrupt:
    flir.release()

@atexit.register
def goodbye():
    print('You are now leaving the Python sector.')


"""
t1 = threading.Thread(target=triggerWatchDog, args=(camIndex,))
t1.setDaemon(True)
t1.start()
"""
