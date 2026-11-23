"use strict";
// Modified by VibeDev (https://github.com/VibeDev-Si/vibedev-bot-plugins/tree/main/draupnir), 2026-11-23:
// senders listed in VIBEDEV_DRAUPNIR_EXEMPT_SENDERS are exempt from this protection (see README there).
// Copyright 2022 Gnuxie <Gnuxie@protonmail.com>
// Copyright 2019, 2020 The Matrix.org Foundation C.I.C.
//
// SPDX-License-Identifier: Apache-2.0
//
// SPDX-FileAttributionText: <text>
// This modified file incorporates work from mjolnir
// https://github.com/matrix-org/mjolnir
// </text>
Object.defineProperty(exports, "__esModule", { value: true });
exports.BasicFloodingProtection = exports.DEFAULT_MAX_PER_MINUTE = void 0;
const matrix_bot_sdk_1 = require("@vector-im/matrix-bot-sdk");
const matrix_protection_suite_1 = require("@the-draupnir-project/matrix-protection-suite");
const typebox_1 = require("@sinclair/typebox");
const log = new matrix_protection_suite_1.Logger("BasicFloodingProtection");
// if this is exceeded, we'll ban the user for spam and redact their messages
exports.DEFAULT_MAX_PER_MINUTE = 10;
const TIMESTAMP_THRESHOLD = 30000; // 30s out of phase
const BasicFloodingProtectionSettings = typebox_1.Type.Object({
    maxPerMinute: typebox_1.Type.Integer({ default: exports.DEFAULT_MAX_PER_MINUTE }),
}, { title: "BasicFloodingProtectionSettings" });
(0, matrix_protection_suite_1.describeProtection)({
    name: "BasicFloodingProtection",
    description: `If a user posts more than ${exports.DEFAULT_MAX_PER_MINUTE} messages in 60s they'll be
    banned for spam. This does not publish the ban to any of your ban lists.
    This is a legacy protection from Mjolnir and contains bugs.`,
    capabilityInterfaces: {
        userConsequences: "UserConsequences",
        eventConsequences: "EventConsequences",
    },
    defaultCapabilities: {
        userConsequences: "StandardUserConsequences",
        eventConsequences: "StandardEventConsequences",
    },
    configSchema: BasicFloodingProtectionSettings,
    factory: async (description, lifetime, protectedRoomsSet, draupnir, capabilities, rawSettings) => {
        const parsedSettings = description.protectionSettings.parseConfig(rawSettings);
        if ((0, matrix_protection_suite_1.isError)(parsedSettings)) {
            return parsedSettings;
        }
        return (0, matrix_protection_suite_1.Ok)(new BasicFloodingProtection(description, lifetime, capabilities, protectedRoomsSet, draupnir, parsedSettings.ok.maxPerMinute));
    },
});
function lastEventsRoomEntry(lastEvents, roomID) {
    const roomEntry = lastEvents.get(roomID);
    if (roomEntry) {
        return roomEntry;
    }
    else {
        const nextEntry = new Map();
        lastEvents.set(roomID, nextEntry);
        return nextEntry;
    }
}
function lastEventsUserEntry(eventsByUser, userID) {
    const userEntry = eventsByUser.get(userID);
    if (userEntry === undefined) {
        const events = [];
        eventsByUser.set(userID, events);
        return events;
    }
    return userEntry;
}
function lastEventsForUser(lastEventsByRoom, roomID, userID) {
    const roomEntry = lastEventsRoomEntry(lastEventsByRoom, roomID);
    const userEvents = lastEventsUserEntry(roomEntry, userID);
    return userEvents;
}
// VibeDev: Matrix user IDs (comma-separated) this protection neither counts nor acts on, such as the VibeDev AI
// assistant, whose answers to several people in a row are not flooding. Empty or unset: the original behaviour.
const VIBEDEV_EXEMPT_SENDERS = new Set((process.env.VIBEDEV_DRAUPNIR_EXEMPT_SENDERS ?? "")
    .split(",")
    .map((sender) => sender.trim())
    .filter((sender) => sender.length > 0));
class BasicFloodingProtection extends matrix_protection_suite_1.AbstractProtection {
    draupnir;
    maxPerMinute;
    lastEvents = new Map();
    recentlyBanned = [];
    userConsequences;
    eventConsequences;
    constructor(description, lifetime, capabilities, protectedRoomsSet, draupnir, maxPerMinute) {
        super(description, lifetime, capabilities, protectedRoomsSet, {});
        this.draupnir = draupnir;
        this.maxPerMinute = maxPerMinute;
        this.userConsequences = capabilities.userConsequences;
        this.eventConsequences = capabilities.eventConsequences;
    }
    async handleTimelineEvent(room, event) {
        // If the sender is draupnir, ignore the message
        if (event["sender"] === this.draupnir.clientUserID) {
            log.debug(`Ignoring message from self: ${event.event_id}`);
            return (0, matrix_protection_suite_1.Ok)(undefined);
        }
        // VibeDev: exempt senders are neither counted nor acted on.
        if (VIBEDEV_EXEMPT_SENDERS.has(event["sender"])) {
            return (0, matrix_protection_suite_1.Ok)(undefined);
        }
        // If the event is a redaction, ignore it.
        // See also: https://github.com/the-draupnir-project/Draupnir/issues/804
        if (event["type"] === "m.room.redaction") {
            log.debug(`Ignoring redaction: ${event.event_id}`);
            return (0, matrix_protection_suite_1.Ok)(undefined);
        }
        const forUser = lastEventsForUser(this.lastEvents, event.room_id, event.sender);
        if (new Date().getTime() - event["origin_server_ts"] >
            TIMESTAMP_THRESHOLD) {
            log.warn("BasicFlooding", `${event["event_id"]} is more than ${TIMESTAMP_THRESHOLD}ms out of phase - rewriting event time to be 'now'`);
            event["origin_server_ts"] = new Date().getTime();
        }
        forUser.push({
            originServerTs: event["origin_server_ts"],
            eventID: event["event_id"],
        });
        // Do some math to see if the user is spamming
        let messageCount = 0;
        for (const prevEvent of forUser) {
            if (new Date().getTime() - prevEvent.originServerTs > 60000)
                continue; // not important
            messageCount++;
        }
        if (messageCount >= this.maxPerMinute) {
            await this.draupnir.managementRoomOutput.logMessage(matrix_bot_sdk_1.LogLevel.WARN, "BasicFlooding", `Banning ${event["sender"]} in ${room.toRoomIDOrAlias()} for flooding (${messageCount} messages in the last minute)`, room.toRoomIDOrAlias());
            if (!this.draupnir.config.noop) {
                await this.userConsequences.consequenceForUserInRoom(room.toRoomIDOrAlias(), event["sender"], "spam");
            }
            else {
                await this.draupnir.managementRoomOutput.logMessage(matrix_bot_sdk_1.LogLevel.WARN, "BasicFlooding", `Tried to ban ${event["sender"]} in ${room.toRoomIDOrAlias()} but Draupnir is running in no-op mode`, room.toRoomIDOrAlias());
            }
            if (this.recentlyBanned.includes(event["sender"])) {
                return (0, matrix_protection_suite_1.Ok)(undefined);
            } // already handled (will be redacted)
            this.draupnir.unlistedUserRedactionQueue.addUser(event["sender"]);
            this.recentlyBanned.push(event["sender"]); // flag to reduce spam
            // Redact all the things the user said too
            if (!this.draupnir.config.noop) {
                for (const eventID of forUser.map((e) => e.eventID)) {
                    await this.eventConsequences.consequenceForEvent(room.toRoomIDOrAlias(), eventID, "spam");
                }
            }
            else {
                await this.draupnir.managementRoomOutput.logMessage(matrix_bot_sdk_1.LogLevel.WARN, "BasicFlooding", `Tried to redact messages for ${event["sender"]} in ${room.toRoomIDOrAlias()} but Draupnir is running in no-op mode`, room.toRoomIDOrAlias());
            }
            // Free up some memory now that we're ready to handle it elsewhere
            forUser.splice(0, forUser.length);
        }
        // Trim the oldest messages off the user's history if it's getting large
        if (forUser.length > this.maxPerMinute * 2) {
            forUser.splice(0, forUser.length - this.maxPerMinute * 2 - 1);
        }
        return (0, matrix_protection_suite_1.Ok)(undefined);
    }
}
exports.BasicFloodingProtection = BasicFloodingProtection;
//# sourceMappingURL=BasicFlooding.js.map