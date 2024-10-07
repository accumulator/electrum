import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Pane {
    id: root
    signal next
    signal finish
    signal prev
    signal accept
    property var wizard_data : ({})
    property bool valid
    property bool last: false
    property string wizard_title: ''
    property string title: ''
    property bool securePage: false

    property QtObject content

    padding: 0
    leftPadding: constants.paddingXLarge
    rightPadding: constants.paddingXLarge

    background: Rectangle {
        color: Material.dialogColor
        TapHandler {
            onTapped: root.forceActiveFocus()
        }
    }

    onAccept: {
        apply()
    }

    // override this in descendants to put data from the view in wizard_data
    function apply() { }

    function checkIsLast() {
        apply()
        last = wizard.wiz.isLast(wizard_data)
    }

    function ensureVisible(item) {
        flickable.ensureVisible(item)
    }

    Component.onCompleted: {
        // NOTE: Use Qt.callLater to execute checkIsLast(), and by extension apply(),
        // otherwise Component.onCompleted handler in descendants is processed
        // _after_ apply() is called, which may lead to setting the wrong
        // wizard_data keys if apply() depends on variables set in descendant
        // Component.onCompleted handler.
        Qt.callLater(checkIsLast)

        // move focus to root of WizardComponent, otherwise Android back button
        // might be missed in Wizard root Item.
        root.forceActiveFocus()
    }

    Flickable {
        id: flickable
        anchors.fill: parent
        clip: true
        interactive: height < contentHeight

        function ensureVisible(item) {
            var ypos = item.mapToItem(contentItem, 0, 0).y
            var ext = item.height + ypos
            if ( ypos < contentY // begins before
                || ypos > contentY + height // begins after
                || ext < contentY // ends before
                || ext > contentY + height) { // ends after
                // don't exceed bounds
                contentY = Math.max(0, Math.min(ypos - height + item.height, contentHeight - height))
            }
        }

        function getFocusedItem() {
            // note: no deep search, only direct children
            for (let i = 0; i < content.children.length; i++) {
                if (content.children[i].activeFocus) {
                    return content.children[i]
                }
            }
            return null
        }
    }

    onContentChanged: {
        flickable.contentItem.children.length = 0 // empty array
        flickable.contentItem.children.push(content)
        flickable.contentHeight = Qt.binding(function() { return content.implicitHeight } )
    }

    Connections {
        target: mainStackView
        function onHeightChanged() {
            let focuseditem = flickable.getFocusedItem()
            if (focuseditem) {
                root.ensureVisible(focuseditem)
            }
        }
    }

}
