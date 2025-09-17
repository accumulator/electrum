import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Controls.Material

import org.electrum 1.0

import "controls"

ElDialog {
    id: dialog

    property string pairing_code
    property QtObject deviceHandler: AppController.deviceHandlerByPairingCode(pairing_code)
    property string message: qsTr('Confirm operation on your hww device')

    title: qsTr('HardwareHandlerDialog')
    width: parent.width
    height: parent.height
    padding: 0

    ColumnLayout {
        width: parent.width
        spacing: 0

        Label {
            text: deviceHandler.deviceInfo()['label']
        }

        Label {
            text: deviceHandler.deviceInfo()['plugin_name']
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
            // root.valid = false
        }
        function onClear_signal() {
            console.log('CLEAR')
            // msglabel.iconStyle = InfoTextArea.IconStyle.Info
            // msglabel.text = ''
            // root.valid = true
        }
    }

}
