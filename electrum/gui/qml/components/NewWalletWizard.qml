import QtQuick
import QtQuick.Layouts
import QtQuick.Controls

import org.electrum 1.0

import "wizard"

Wizard {
    id: walletwizard
    wizardTitle: qsTr('New Wallet')

    signal walletCreated

    property string path
    property var initial_data
    property string initial_view

    wiz: Daemon.newWalletWizard

    Component.onCompleted: {
        console.log(initial_view)
        console.log(initial_data)
        var view
        if (initial_view == undefined)
            view = wiz.startWizard()
        else
            view = wiz.startWizard(initial_view, initial_data)

        _loadNextComponent(view)
    }

    onAccepted: {
        console.log('Finished new wallet wizard')
        wiz.createStorage(wizard_data, Daemon.singlePasswordEnabled, Daemon.singlePassword)
    }

    Connections {
        target: wiz
        function onCreateSuccess() {
            walletwizard.path = wiz.path
            walletwizard.walletCreated()
        }
        function onCreateError(error) {
            var dialog = app.messageDialog.createObject(app, {
                title: qsTr('Error'),
                iconSource: Qt.resolvedUrl('../../icons/warning.png'),
                text: error
            })
            dialog.open()
        }
    }
}

