import QtQuick 2.12
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.0
import QtQuick.Controls.Material 2.0
import QtQml.Models 2.2

import org.electrum 1.0

import "controls"

Pane {
    id: rootItem
    visible: Daemon.currentWallet
    padding: 0
    clip: true

    background: Rectangle {
        color: constants.darkerBackground
    }

    Item {
        id: drawer
        width: parent.width
        height: drawerLayout.height
        y: -height

        property int _ystart

        ColumnLayout {
            id: drawerLayout
            anchors.horizontalCenter: parent.horizontalCenter

            Item { width: 1; height: constants.paddingXLarge }
            BalanceSummary {
                id: bs
            }
            Item { width: 1; height: constants.paddingXLarge }
        }

        function start() {
            _ystart = drawer.y
        }

        function setYPos(y) {
            var newY = _ystart + y
            drawer.y = Math.min(0, Math.max(newY, -drawer.height))
        }
    }

    ListView {
        id: listview
        width: parent.width
        anchors.bottom: parent.bottom
        anchors.top: drawer.bottom
        clip: true

        boundsBehavior: Flickable.StopAtBounds
        model: visualModel

        DragHandler {
            xAxis.enabled: false
            yAxis.enabled: listview.atYBeginning
            yAxis.minimum: 0
            yAxis.maximum: drawer.height
            target: null
            onActiveChanged: {
                console.log('dh active=' + active)
                if (active) drawer.start()
            }
            onTranslationChanged: {
                console.log('xlat changed, y=' + translation.y)
                drawer.setYPos(translation.y)
            }
        }

        readonly property variant sectionLabels: {
            'today': qsTr('Today'),
            'yesterday': qsTr('Yesterday'),
            'lastweek': qsTr('Last week'),
            'lastmonth': qsTr('Last month'),
            'older': qsTr('Older')
        }

        section.property: 'section'
        section.criteria: ViewSection.FullString
        section.delegate: RowLayout {
            width: ListView.view.width
            required property string section
            Label {
                text: listview.sectionLabels[section]
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: constants.paddingLarge
                font.pixelSize: constants.fontSizeLarge
                color: Material.accentColor
            }
        }

        DelegateModel {
            id: visualModel
            model: Daemon.currentWallet.historyModel

            groups: [
                DelegateModelGroup { name: 'today'; includeByDefault: false },
                DelegateModelGroup { name: 'yesterday'; includeByDefault: false },
                DelegateModelGroup { name: 'lastweek'; includeByDefault: false },
                DelegateModelGroup { name: 'lastmonth'; includeByDefault: false },
                DelegateModelGroup { name: 'older'; includeByDefault: false }
            ]

            delegate: HistoryItemDelegate {
            }
        }

        ScrollIndicator.vertical: ScrollIndicator { }

    }

    MouseArea {
        id: vdragscroll
        anchors {
            top: listview.top
            right: listview.right
            bottom: listview.bottom
        }
        width: constants.paddingXXLarge
        drag.target: dragb
        onPressedChanged: if (pressed) {
            dragb.y = mouseY + listview.y - dragb.height/2
        }
    }

    Rectangle {
        id: dragb
        anchors.right: vdragscroll.left
        width: postext.width + constants.paddingXXLarge
        height: postext.height + constants.paddingXXLarge
        radius: constants.paddingXSmall

        color: constants.colorAlpha(Material.accentColor, 0.33)
        border.color: Material.accentColor
        opacity : vdragscroll.drag.active ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 300 } }

        onYChanged: {
            if (vdragscroll.drag.active) {
                listview.contentY =
                    Math.max(listview.originY,
                    Math.min(listview.contentHeight - listview.height + listview.originY,
                        ((y-listview.y)/(listview.height - dragb.height)) * (listview.contentHeight - listview.height + listview.originY) ))
            }
        }
        Label {
            id: postext
            anchors.centerIn: parent
            text: listview.itemAt(0,listview.contentY + (dragb.y + dragb.height/2)).delegateModel.date
            font.pixelSize: constants.fontSizeLarge
        }
    }

    Connections {
        target: Network
        function onHeightChanged(height) {
            Daemon.currentWallet.historyModel.updateBlockchainHeight(height)
        }
    }
}
