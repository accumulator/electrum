import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import org.electrum 1.0

import "../controls"

WizardComponent {
    id: root

    property QtObject deviceHandler: AppController.deviceHandler(wizard_data['hardware_uid'])
    property string message

    function apply() {
        var xpub_data = deviceHandler.xpubData()
        // Nothing retrieved (yet), e.g. when checkIsLast() runs before the retrieval has finished.
        if (!('master_key' in xpub_data))
            return
        wizard_data['hw_type'] = xpub_data['hw_type']
        wizard_data['master_key'] = xpub_data['master_key']
        wizard_data['root_fingerprint'] = xpub_data['root_fingerprint']
        wizard_data['label'] = xpub_data['label']
        wizard_data['soft_device_id'] = xpub_data['soft_device_id']
    }

    ColumnLayout {
        width: parent.width
        spacing: constants.paddingLarge

        Label {
            Layout.alignment: Qt.AlignTop
            Layout.fillWidth: true
            text: qsTr('Retrieving master public key')
        }

        TextHighlightPane {
            Layout.fillWidth: true
            backgroundColor: constants.darkerDialogBackground
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
        wiz.hwwGetXpub(wizard_data['hardware_uid'])
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
        function onXpub_available() {
            root.valid = true
        }
    }

    onPrev: {
        console.log('prev, abort')
        // deviceHandler.abort()
        deviceHandler.cancelShowMessage()
    }
}
