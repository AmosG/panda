PANDA.routers.Index = Backbone.Router.extend({
    routes: {
        "activate/:activation_key":                     "activate",
        "login":                                        "login",
        "logout":                                       "logout",
        "":                                             "search",
        "search/:query":                                "search",
        "search/:query/:limit":                         "search",
        "search/:query/:limit/:page":                   "search",
        "upload":                                       "data_upload",
        "dataset/:dataset_slug/upload":                 "data_upload",
        "datasets":                                     "datasets_search",
        "datasets/:query":                              "datasets_search",
        "datasets/:query/:limit":                       "datasets_search",
        "datasets/:query/:limit/:page":                 "datasets_search",
        "category/:slug":                               "category",
        "category/:slug/:query":                        "category",
        "category/:slug/:query/:limit":                 "category",
        "category/:slug/:query/:limit/:page":           "category",
        "dataset/:slug":                                "dataset_view",
        "dataset/:slug/edit":                           "dataset_edit",
        "dataset/:slug/search/:query":                  "dataset_search",
        "dataset/:slug/search/:query/:limit":           "dataset_search",
        "dataset/:slug/search/:query/:limit/:page":     "dataset_search",
        "*path":                                        "not_found"
    },

    initialize: function(options) {
        this.controller = options.controller;
    },

    activate: function(activation_key) {
        this.controller.goto_activate(activation_key);
    },

    login: function() {
        this.controller.goto_login();
    },

    logout: function() {
        this.controller.goto_logout();
    },

    search: function(query, limit, page) {
        this.controller.goto_search(query, limit, page);
    },

    data_upload: function(dataset_slug) {
        this.controller.goto_data_upload(dataset_slug);
    },

    datasets_search: function(query, limit, page) {
        this.controller.goto_datasets_search(null, query, limit, page);
    },

    category: function(slug, query, limit, page) {
        this.controller.goto_datasets_search(slug, query, limit, page);
    },

    dataset_view: function(slug) {
        this.controller.goto_dataset_view(slug);
    },

    dataset_edit: function(slug) {
        this.controller.goto_dataset_edit(slug);
    },

    dataset_search: function(slug, query, limit, page) {
        this.controller.goto_dataset_search(slug, query, limit, page);
    },

    not_found: function(path) {
        this.controller.goto_not_found();
    }
});
