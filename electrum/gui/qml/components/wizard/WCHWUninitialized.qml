import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import org.electrum 1.0

import "../controls"

WizardComponent {
    id: root
    valid: false  // the device has to be initialized first, the user can only go back

    property QtObject deviceHandler: AppController.deviceHandler(wizard_data['hardware_uid'])

    ColumnLayout {
        width: parent.width
        spacing: constants.paddingLarge

        InfoTextArea {
            Layout.fillWidth: true
            iconStyle: InfoTextArea.IconStyle.Warn
            backgroundColor: constants.darkerDialogBackground
            text: qsTr('This %1 is not initialized. Use manufacturer tooling to initialize the device.')
                .arg(deviceHandler.deviceInfo()['model_name'])
        }
    }
}
