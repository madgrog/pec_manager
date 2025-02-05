/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: "Chatter",
    recordMethods: {
        // onClickSendMessage(ev) {
        //     if (this.composerView && !this.composerView.composer.isLog) {
        //         this.composerView.onClickFullComposer();
        //     } else {
        //         console.log("custom onClickSendMessage")
        //         this.showSendMessage();
        //         this.composerView.onClickFullComposer();
        //     }
        // },
    }
})
