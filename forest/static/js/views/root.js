PANDA.views.Root = Backbone.View.extend({
    el: $("body"),

    views: {},

    _current_user: null,
    current_content_view: null,

    initialize: function() {
        // Override Backbone's sync handler with the authenticated version
        Backbone.noAuthSync = Backbone.sync;
        Backbone.sync = _.bind(this.sync, this);

        // Setup global router
        this.router = new PANDA.routers.Index({ controller: this });

        // Attempt to authenticate from cookies
        this.authenticate();

        // Configure the global topbar
        this.configure_topbar();

        return this;
    },

    start_routing: function() {
        // Begin routing
        Backbone.history.start();
    },

    authenticate: function() {
        /*
         * Verifies that the current user is authenticated, first by checking
         * for an active user and then by checking for a cookie. Redirects
         * to login if authentication fails.
         */
        if (this._current_user) {
            return true;
        }

        email = $.cookie("email");
        api_key = $.cookie("api_key");

        if (email && api_key) {
            this.set_current_user(new PANDA.models.User({ "email": email, "api_key": api_key }));

            // Fetch latest notifications (doubles as a verification of the user's credentials)
            this._current_user.refresh_notifications(_.bind(this.configure_topbar, this));

            return true;
        }

        window.location = "#login";

        return false;
    },

    get_current_user: function() {
        /*
         * Gets the current system user.
         */
        return this._current_user;
    },

    set_current_user: function(user) {
        /*
         * Sets the current system user. Assumes that user has already authenticated.
         */
        this._current_user = user;

        if (this._current_user) {
            $.cookie('email', this._current_user.get("email"));
            $.cookie('api_key', this._current_user.get("api_key"));
        } else {
            $.cookie('email', null);
            $.cookie('api_key', null);
        }
            
        this.configure_topbar();
    },

    ajax: function(options) {
        /*
         * Makes an authenticated ajax request to the API.
         */
        var dfd = new $.Deferred();

        this.authenticate();

        // Handle authentication failures
        dfd.fail(function(responseXhr, status, error) {
            if (responseXhr.status == 401) {
                this.set_current_user(null);
                window.location = "#login";
            }
        });

        // Trigger original error handler after checking for auth issues
        dfd.fail(options.error);
        options.error = dfd.reject;

        dfd.request = $.ajax(options);

        return dfd;
    },

    sync: function(method, model, options) {
        /*
         * Custom Backbone sync handler to attach authorization headers
         * and handle failures.
         */
        var dfd = new $.Deferred();

        this.authenticate();

        // Handle authentication failures
        dfd.fail(function(xhr, status, error) {
            if (xhr.status == 401) {
                window.location = "#login";
            }
        });

        // Trigger original error handler after checking for auth issues
        dfd.fail(options.error);
        options.error = dfd.reject;

        dfd.request = Backbone.noAuthSync(method, model, options);

        return dfd;
    },

    configure_topbar: function() {
        /*
         * Reconfigures the Bootstrap topbar based on the current user.
         */
        if (!this._current_user) {
            $("#topbar-email").hide();
            $("#topbar-notifications").hide();
            $("#topbar-logout").hide();
            $("#topbar-login").css("display", "block");
            $("#topbar-register").css("display", "block");
        } else {
            $("#topbar-email a").text(this._current_user.get("email"));

            $("#topbar-notifications .dropdown-menu").html("");

            if (this._current_user.notifications.models.length > 0) {
                $("#topbar-notifications .count").addClass("important");

                this._current_user.notifications.each(function(note) {
                    related_dataset = note.get("related_dataset");

                    if (related_dataset) {
                        slash = related_dataset.lastIndexOf("/", related_dataset.length - 2);
                        link = "#dataset/" + related_dataset.substring(slash + 1, related_dataset.length - 1);
                    } else {
                        link = "#";
                    }

                    $("#topbar-notifications .dropdown-menu").append('<li><a href="' + link + '">' + note.get("message") + '</a></li>');
                });
            } else {
                $("#topbar-notifications .count").removeClass("important");
            }
            
            $("#topbar-notifications .count").text(this._current_user.notifications.length);

            $("#topbar-email").css("display", "block");
            $("#topbar-notifications").css("display", "block");
            $("#topbar-logout").css("display", "block");
            $("#topbar-login").hide();
            $("#topbar-register").hide();
        }
    },

    get_or_create_view: function(name, options) {
        /*
         * Register each view as it is created and never create more than one.
         */
        if (name in this.views) {
            return this.views[name];
        }

        this.views[name] = new PANDA.views[name](options);

        return this.views[name];
    },

    goto_login: function() {
        this.current_content_view = this.get_or_create_view("Login");
        this.current_content_view.reset();
    },
    
    goto_logout: function() {
        this.set_current_user(null);

        window.location = "#login";
    },

    goto_register: function() {
        this.current_content_view = this.get_or_create_view("Register");
        this.current_content_view.reset();
    },

    goto_search: function(query, limit, page) {
        // This little trick avoids rerendering the Search view if
        // its already visible. Only the nested results need to be
        // rerendered.
        if (!this.authenticate()) {
            return;
        }

        if (!(this.current_content_view instanceof PANDA.views.Search)) {
            this.current_content_view = this.get_or_create_view("Search");
            this.current_content_view.reset(query);
        }

        this.current_content_view.search(query, limit, page);
    },

    goto_upload: function() {
        if (!this.authenticate()) {
            return;
        }

        this.current_content_view = this.get_or_create_view("Upload");
        this.current_content_view.reset();
    },

    goto_list_datasets: function(limit, page) {
        if (!this.authenticate()) {
            return;
        }

        this.current_content_view = this.get_or_create_view("ListDatasets");
        this.current_content_view.reset(limit, page);
    },

    goto_edit_dataset: function(id) {
        if (!this.authenticate()) {
            return;
        }

        resource_uri = PANDA.API + "/dataset/" + id + "/";

        d = new PANDA.models.Dataset({ resource_uri: resource_uri });

        d.fetch({ success: _.bind(function() {
            this.current_content_view = this.get_or_create_view("EditDataset");
            this.current_content_view.dataset = d;
            this.current_content_view.reset();
        }, this)});
    },

    goto_search_dataset: function(id, query, limit, page) {
        if (!this.authenticate()) {
            return;
        }

        if (!(this.current_content_view instanceof PANDA.views.DatasetSearch)) {
            this.current_content_view = this.get_or_create_view("DatasetSearch");
            this.current_content_view.reset(id, query);
        }

        this.current_content_view.search(query, limit, page);
    },

    goto_not_found: function(path) {
        if (!(this.current_content_view instanceof PANDA.views.NotFound)) {
            this.current_content_view = this.get_or_create_view("NotFound");
            this.current_content_view.reset(path);
        }

        this.current_content_view.reset(path);
    }
});
