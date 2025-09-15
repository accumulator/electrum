import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Controls.Material

import org.electrum 1.0

import "../controls"

WizardComponent {
    id: root
    valid: hardwareListView.model.count && hardwareListView.currentIndex >= 0

    property string fail_msg
    property int cosigner: 0

    function apply() {
        // NOTE: qml here stores a serializable device id, the backing object retrieves the
        // corresponding DeviceInfo object in the wizard accept handler.
        var device_uid = hardwareListView.currentItem.device_uid
        if (cosigner) {
            wizard_data['multisig_cosigner_data'][cosigner.toString()]['hardware_uid'] = device_uid
        } else {
            wizard_data['hardware_uid'] = device_uid
        }
    }

    function rescan() {
        fail_msg = ''
        hardwareListView.model.initModel()
    }

    ColumnLayout {
        width: parent.width
        height: parent.height

        InfoTextArea {
            Layout.fillWidth: true
            text: qsTr('Choose hardware device')
            iconStyle: hardwareListView.model.busy
                ? InfoTextArea.IconStyle.Spinner
                : InfoTextArea.IconStyle.Info
        }

        ElListView {
            id: hardwareListView
            Layout.fillHeight: true
            Layout.fillWidth: true
            model: Daemon.hardwareListModel

            delegate: ItemDelegate {
                id: delegate
                property string device_uid: model.device_uid
                width: ListView.view.width
                onClicked: hardwareListView.currentIndex = index
                RowLayout {
                    width: parent.width
                    RadioButton {
                        checked: delegate.ListView.isCurrentItem
                    }

                    Label {
                        Layout.fillWidth: true
                        text: model.label
                        wrapMode: Text.Wrap
                    }
                }
            }

            footer:  ColumnLayout {
                width: ListView.view.width
                visible: !hardwareListView.model.busy
                Item {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: constants.paddingLarge
                }
                Label {
                    visible: !hardwareListView.model.count
                    Layout.fillWidth: true
                    text: root.fail_msg
                    wrapMode: Text.Wrap
                }
                Button {
                    Layout.alignment: Qt.AlignHCenter
                    text: qsTr('Rescan')
                    onClicked: rescan()
                }
            }
        }

    }

    Connections {
        target: Daemon.hardwareListModel
        function onScanFailed(code, msg) {
            console.log('scan failed: ' + msg)
            root.fail_msg = msg
        }
    }

    Component.onCompleted: {
        if (wizard_data['wallet_type'] == 'multisig') {
            if ('multisig_current_cosigner' in wizard_data)
                cosigner = wizard_data['multisig_current_cosigner']
        }
        // rescan()
    }

}
