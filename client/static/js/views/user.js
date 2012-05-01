PANDA.views.User = Backbone.View.extend({
    el: $("#content"),

    user: null,
    datasets: null,

    edit_view: null,
    change_password_view: null,

    initialize: function(options) {
        _.bindAll(this);
        
        this.edit_view = new PANDA.views.UserEdit();
        this.change_password_view = new PANDA.views.UserChangePassword();
    },

    reset: function(id) {
        this.user = new PANDA.models.User({ resource_uri: PANDA.API + "/user/" + id + "/" });
        this.datasets = new PANDA.collections.Datasets();

        this.user.fetch({
            async: false,
            success: _.bind(function(model, response) {
                this.datasets.fetch({
                    data: {
                        creater_email: this.user.get("email"),
                        simple: true,
                        limit: 1000
                    },
                    success: _.bind(function(model, response) {
                        this.render();
                    }, this),
                    error: _.bind(function(model, response) {
                        if (response.status == 404) {
                            Redd.goto_not_found(); 
                        } else {
                            Redd.goto_server_error();
                        }
                    }, this)
                });

                this.edit_view.set_user(this.user);
                this.change_password_view.set_user(this.user);
            }, this),
            error: _.bind(function(model, response) {
                if (response.status == 404) {
                    Redd.goto_not_found(); 
                } else {
                    Redd.goto_server_error();
                }
            }, this)
        });
    },

    render: function() {
        // Nuke old modals
        $("#modal-edit-user").remove();

        var context = PANDA.utils.make_context({
            user: this.user.toJSON(),
            datasets: this.datasets.results(),
            current_user: Redd.get_current_user().toJSON() 
        });

        this.el.html(PANDA.templates.user(context));

        this.edit_view.el = $("#modal-edit-user");
        $("#user-edit").click(this.edit);
        
        this.change_password_view.el = $("#modal-user-change-password");
        $("#user-change-password").click(this.change_password);
    },

    edit: function() {
        this.edit_view.render();
        $("#modal-edit-user").modal("show");
    },

    change_password: function() {
        this.change_password_view.render();
        $("#modal-user-change-password").modal("show");
    }
});

