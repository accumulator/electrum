import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import org.electrum 1.0

import "../controls"

WizardComponent {
    id: root

    property QtObject deviceHandler: AppController.deviceHandler(wizard_data['hardware_uid'])

    ColumnLayout {
        width: parent.width
        height: parent.height

        Label {
            Layout.alignment: Qt.AlignTop
            Layout.fillWidth: true
            text: qsTr('Unlock hardware wallet')
        }

        InfoTextArea {
            id: msglabel
            Layout.fillWidth: true
            visible: text
        }
    }

    Component.onCompleted: {
        wiz.unlockHww(wizard_data['hardware_uid'])
    }

    Connections {
        target: deviceHandler
        function onMessage_signal(msg, onc) {
            console.log(msg)
            msglabel.text = msg
            msglabel.iconStyle = InfoTextArea.IconStyle.Info
        }
        function onError_signal(msg) {
            console.log('error: ' + msg)
            msglabel.text = msg
            msglabel.iconStyle = InfoTextArea.IconStyle.Error
            root.valid = false
        }
        function onClear_signal() {
            msglabel.text = ''
            // root.valid = true
        }
        function onPassword_available() {
            root.valid = true
        }
    }

    onPrev: {
        console.log('prev, abort')
        // deviceHandler.abort()
        deviceHandler.cancelShowMessage()
    }
}
