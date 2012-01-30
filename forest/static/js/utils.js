/*
 * This module contains global utilities--mostly jQuery extension.
 */

if (typeof String.prototype.startsWith != 'function') {
    String.prototype.startsWith = function (str) {
        return this.slice(0, str.length) == str;
    };
}

$.fn.serializeObject = function() {
    /*
     * Serialize a form to a Javascript object.
     */
    var obj = {};
    var arr = this.serializeArray();

    $.each(arr, function() {
        if (obj[this.name] !== undefined) {
            if (!obj[this.name].push) {
                obj[this.name] = [obj[this.name]];
            }
            obj[this.name].push(this.value || '');
        } else {
            obj[this.name] = this.value || '';
        }
    });

    return obj;
};

$.fn.alert = function(type, message, close_button) {
    /*
     * Display a Twitter bootstrap alert with an optional close button.
     */
    this.hide();
    this.removeClass("warning error success info").addClass(type);

    if (_.isUndefined(close_button)) {
        close_button = true;
    }

    if (close_button) {
        this.html("<a class=\"close\" href=\"#\">×</a>" + message);
    } else {
        this.html(message);
    }

    this.show();
}

$.fn.show_errors = function(errors, alert_prefix) {
    /*
     * Takes a set of errors in the Django-forms format:
     * { "field_id": ["error1", "error2" ] }
     * and displays them on a Twitter Bootstrap form.
     */
    if (!alert_prefix) {
        alert_prefix = "";
    }

    // Clear old errors
    $(this).find(".alert-message").hide();
    $(this).find("div.clearfix").removeClass("error");
    $(this).find(".help-inline").text("");

    // Show global errors in an alert
    if ("__all__" in errors) {
        $(this).find(".alert-message").alert("error block-message", "<p><strong>" + alert_prefix + "</strong> " + errors["__all__"] + ".");
    }

    _.each(errors, _.bind(function(field_errors, field) {
        // Only render one error at a time
        var error = field_errors[0];

        var input = $(this).find('input[name="' + field + '"]');

        if (input) {
            input.parents("div.clearfix").addClass("error");
            input.siblings(".help-inline").text(error);
        }
    }, this));
}

moment.fn.toLocalTimezone = function() {
    /*
     * Convert UTC datetimes to the user's local timezone.
     */
    return this.subtract("minutes", this._d.getTimezoneOffset());
}

$(".alert-message .close").live("click", function() {
    /*
     * Close handler for alerts.
     */
    $(this).parent().hide();
    
    return false;
});

$(".modal-close").live("click", function() {
    /*
     * Close handler for modal dialogs.
     */
    $(this).parents(".modal").modal("hide");
});

$(".scroll-up").live("click", function() {
    /*
     * Handler for UI elements that should reset the viewport (pseudo-paging).
     */
    window.scrollTo(0, 0);
});

