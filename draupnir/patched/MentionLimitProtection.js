"use strict";
// Modified by VibeDev (https://github.com/VibeDev-Si/vibedev-bot-plugins/tree/main/draupnir), 2026-11-23:
// senders listed in VIBEDEV_DRAUPNIR_EXEMPT_SENDERS are exempt from this protection (see README there).
// Copyright 2024 - 2025 Gnuxie <Gnuxie@protonmail.com>
// Copyright 2024 The Matrix.org Foundation C.I.C.
//
// SPDX-License-Identifier: Apache-2.0
Object.defineProperty(exports, "__esModule", { value: true });
exports.MentionLimitProtection = void 0;
exports.isContainingMentionsOverLimit = isContainingMentionsOverLimit;
const matrix_protection_suite_1 = require("@the-draupnir-project/matrix-protection-suite");
const typebox_1 = require("@sinclair/typebox");
const LeakyBucket_1 = require("../queues/LeakyBucket");
const interface_manager_1 = require("@the-draupnir-project/interface-manager");
const mps_interface_adaptor_1 = require("@the-draupnir-project/mps-interface-adaptor");
const log = new matrix_protection_suite_1.Logger("MentionLimitProtection");
function isMentionsMixinOverLimit(mentionsMixin, maxMentions) {
    return mentionsMixin.user_ids.length > maxMentions;
}
function isContentContaningMentionsOverLimit(content, maxMentions, checkBody) {
    const mentionMixin = content.findMixin(matrix_protection_suite_1.MentionsMixinDescription);
    if (mentionMixin?.isErroneous === false &&
        isMentionsMixinOverLimit(mentionMixin, maxMentions)) {
        return true;
    }
    if (!checkBody) {
        return false;
    }
    const bodyMixin = content.findMixin(matrix_protection_suite_1.RoomMessageBodyMixinDescription);
    if (bodyMixin === undefined || bodyMixin.isErroneous) {
        return false;
    }
    return bodyMixin.body.split("@").length - 1 > maxMentions;
}
function isContainingMentionsOverLimit(event, maxMentions, checkBody) {
    const isTopContentOverLimit = isContentContaningMentionsOverLimit(event, maxMentions, checkBody);
    if (isTopContentOverLimit) {
        return true;
    }
    const newContentMixin = event.findMixin(matrix_protection_suite_1.NewContentMixinDescription);
    if (newContentMixin === undefined || newContentMixin.isErroneous) {
        return false;
    }
    return isContentContaningMentionsOverLimit(newContentMixin, maxMentions, checkBody);
}
const MentionLimitProtectionSettings = typebox_1.Type.Object({
    maxMentions: typebox_1.Type.Integer({
        description: "The maximum number of mentions permitted.",
        default: 3,
    }),
    warningText: typebox_1.Type.String({
        description: "The reason to use to notify the user after redacting their infringing message.",
        default: "You have mentioned too many users in this message, so we have had to redact it.",
    }),
    includeLegacyMentions: typebox_1.Type.Boolean({
        description: "Whether to scrape the body for legacy mentions, can lead to more false positives.",
        default: false,
    }),
}, {
    title: "MentionLimitProtectionSettings",
});
// VibeDev: Matrix user IDs (comma-separated) this protection neither counts nor acts on, such as the VibeDev AI
// assistant, whose answers to several people in a row are not flooding. Empty or unset: the original behaviour.
const VIBEDEV_EXEMPT_SENDERS = new Set((process.env.VIBEDEV_DRAUPNIR_EXEMPT_SENDERS ?? "")
    .split(",")
    .map((sender) => sender.trim())
    .filter((sender) => sender.length > 0));
class MentionLimitProtection extends matrix_protection_suite_1.AbstractProtection {
    roomMessageSender;
    eventConsequences;
    userConsequences;
    warningText;
    maxMentions;
    includeLegacymentions;
    consequenceBucket = new LeakyBucket_1.LazyLeakyBucket(1, 30 * 60_000 // half an hour will do
    );
    constructor(description, lifetime, capabilities, roomMessageSender, protectedRoomsSet, settings) {
        super(description, lifetime, capabilities, protectedRoomsSet, {});
        this.roomMessageSender = roomMessageSender;
        this.eventConsequences = capabilities.eventConsequences;
        this.userConsequences = capabilities.userConsequences;
        this.maxMentions = settings.maxMentions;
        this.warningText = settings.warningText;
        this.includeLegacymentions = settings.includeLegacyMentions;
    }
    handleTimelineEventMixins(_room, event) {
        if (event.sourceEvent.sender === this.protectedRoomsSet.userID) {
            return;
        }
        // VibeDev: exempt senders are not acted on.
        if (VIBEDEV_EXEMPT_SENDERS.has(event.sourceEvent.sender)) {
            return;
        }
        if (isContainingMentionsOverLimit(event, this.maxMentions, this.includeLegacymentions)) {
            void (0, matrix_protection_suite_1.Task)(this.handleEventOverLimit(event), {
                log,
            });
        }
    }
    async handleEventOverLimit(event) {
        const sourceEvent = event.sourceEvent;
        const infractions = this.consequenceBucket.getTokenCount(sourceEvent.sender);
        if (infractions > 0) {
            const userResult = await this.userConsequences.consequenceForUserInRoom(sourceEvent.room_id, sourceEvent.sender, this.warningText);
            if ((0, matrix_protection_suite_1.isError)(userResult)) {
                log.error("Failed to ban the user", sourceEvent.sender, userResult.error);
            }
            // fall through to the event consequence on purpose so we redact the event too.
        }
        else {
            // if they're not being banned we need to tell them why their message got redacted.
            void (0, matrix_protection_suite_1.Task)((0, mps_interface_adaptor_1.sendMatrixEventsFromDeadDocument)(this.roomMessageSender, sourceEvent.room_id, interface_manager_1.DeadDocumentJSX.JSXFactory("root", null,
                (0, mps_interface_adaptor_1.renderMentionPill)(sourceEvent.sender, sourceEvent.sender),
                " ",
                this.warningText), { replyToEvent: sourceEvent }), {
                log,
            });
        }
        this.consequenceBucket.addToken(sourceEvent.sender);
        return await this.eventConsequences.consequenceForEvent(sourceEvent.room_id, sourceEvent.event_id, this.warningText);
    }
    handleProtectionDisable() {
        this.consequenceBucket.stop();
    }
}
exports.MentionLimitProtection = MentionLimitProtection;
(0, matrix_protection_suite_1.describeProtection)({
    name: "MentionLimitProtection",
    description: `A potection that will remove any messages with
    a number of mentions over a preconfigured limit.
    Please read the documentation https://the-draupnir-project.github.io/draupnir-documentation/protections/mention-limit-protection.`,
    capabilityInterfaces: {
        eventConsequences: "EventConsequences",
        userConsequences: "UserConsequences",
    },
    defaultCapabilities: {
        eventConsequences: "StandardEventConsequences",
        userConsequences: "StandardUserConsequences",
    },
    configSchema: MentionLimitProtectionSettings,
    factory: async (decription, lifetime, protectedRoomsSet, draupnir, capabilitySet, settings) => (0, matrix_protection_suite_1.allocateProtection)(lifetime, new MentionLimitProtection(decription, lifetime, capabilitySet, draupnir.clientPlatform.toRoomMessageSender(), protectedRoomsSet, settings)),
});
//# sourceMappingURL=MentionLimitProtection.js.map