import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import org.electrum 1.0

import "../controls"

WizardComponent {
    id: root

    property QtObject deviceHandler: AppController.deviceHandler(wizard_data['hardware_uid'])
    property string message

    ColumnLayout {
        width: parent.width
        spacing: constants.paddingLarge

        Label {
            Layout.alignment: Qt.AlignTop
            Layout.fillWidth: true
            text: qsTr('Unlock hardware wallet')
        }

        TextHighlightPane {
            Layout.fillWidth: true
            RowLayout {
                width: parent.width
                spacing: constants.paddingLarge
                Image {
                    id: image
                    source: deviceHandler.icon('unpaired')
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Label {
                        Layout.fillWidth: true
                        text: message
                        wrapMode: Text.Wrap
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        wiz.unlockHww(wizard_data['hardware_uid'])
    }

    Connections {
        target: deviceHandler
        function onMessage_signal(msg, onc) {
            console.log(msg)
            message = msg
            // msglabel.iconStyle = InfoTextArea.IconStyle.Spinner
        }
        function onError_signal(msg) {
            console.log('error: ' + msg)
            message = msg
            // msglabel.iconStyle = InfoTextArea.IconStyle.Error
            root.valid = false
        }
        function onClear_signal() {
            console.log('CLEAR')
            // msglabel.iconStyle = InfoTextArea.IconStyle.Info
            // msglabel.text = ''
            // root.valid = true
        }
        function onPassword_available() {
            root.valid = true
            wizard.requestNextOrFinish()
        }
    }

    onPrev: {
        console.log('prev, abort')
        // deviceHandler.abort()
        deviceHandler.cancelShowMessage()
    }
}
