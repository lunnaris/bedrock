/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

// needs to execute on DOM ready to sync with core-data-layer.init.js in GA.
$(function() {
    'use strict';

    var client = window.Mozilla.Client;
    var utils = window.Mozilla.Utils;

    var headingText;
    var messageText;
    var confirmText;
    var confirmActionText;
    var confirmLabelText;
    var closeText;

    // try to get localized copy
    if (typeof utils !== 'undefined') {
        headingText = utils.trans('global-fx-out-of-date-banner-heading');
        messageText = utils.trans('global-fx-out-of-date-banner-message');
        confirmText = utils.trans('global-fx-out-of-date-banner-confirm');
        confirmActionText = utils.trans('global-fx-out-of-date-banner-confirm-action');
        confirmLabelText = utils.trans('global-fx-out-of-date-banner-confirm-label');
        closeText = utils.trans('global-close');
    // fall back to English copy if we can't get to the trans function for some reason
    } else {
        headingText = 'Your Firefox is out-of-date.';
        messageText = 'Get the most recent version to keep browsing securely.';
        confirmText = 'Update Firefox';
        confirmActionText = 'Update Firefox';
        confirmLabelText = 'Firefox for Desktop';
        closeText = 'Close';
    }

    var options = [{
        'id': 'fx-out-of-date-banner',
        'name': 'fx-out-of-date',
        'heading': headingText,
        'message': messageText,
        'confirm': confirmText,
        'confirmAction': confirmActionText,
        'confirmLabel': confirmLabelText,
        'url': '/firefox/new/?scene=2',
        'close': closeText,
        'closeLabel': closeText
    }];

    // Set a unique cookie ID for fx-out-of-date notification.
    Mozilla.NotificationBanner.COOKIE_CODE_ID = 'moz-notification-fx-out-of-date';

    // Notification should only be shown to users on Firefox for desktop.
    if (client.isFirefoxDesktop) {
        client.getFirefoxDetails(function(details) {
            // User must be out of date and on release channel.
            if (!details.isUpToDate && details.channel === 'release') {

                // Check that cookies are enabled before seeing if one already exists.
                if (typeof Mozilla.Cookies !== 'undefined' && Mozilla.Cookies.enabled()) {
                    var choice = Mozilla.NotificationBanner.getOptions(options);

                    if (choice) {
                        Mozilla.NotificationBanner.init(choice);
                    }
                }
            }
        });
    }
});
