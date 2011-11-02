PANDA.views.EditDataset = Backbone.View.extend({
    el: $("#content"),
    
    template: PANDA.templates.edit_dataset,
    dataset: null,

    events: {
        "click #dataset-save":      "save",
        "click #dataset-download":  "download"
    },

    initialize: function() {
        _.bindAll(this, "render", "save", "destroy", "download");

        $("#dataset-destroy").live("click", this.destroy);
    },

    reset: function() {
        this.render();
    },

    render: function() {
        this.el.html(this.template(this.dataset.toJSON()));

        task = this.dataset.current_task;

        if (task && task.get("task_name") == "redd.tasks.DatasetImportTask") {
            if (task.get("status") == "STARTED") {
                $("#edit-dataset-alert").alert("info block-message", "<p><strong>Import in progress!</strong> This dataset is currently being made searchable. It will not yet appear in search results.</p>Status of import: " + task.get("message") + ".");
            } else if (task.get("status") == "PENDING") {
                $("#edit-dataset-alert").alert("info block-message", "<p><strong>Queued for import!</strong> This dataset is currently waiting to be made searchable. It will not yet appear in search results.</p>");
            } else if (task.get("status") == "FAILURE") {
                $("#edit-dataset-alert").alert("error block-message", "<p><strong>Import failed!</strong> The process to make this dataset searchable failed. It will not appear in search results.");
            } 
        }
    },

    save: function() {
        form_values = $("#edit-dataset-form").serializeObject();

        s = {};

        _.each(form_values, _.bind(function(v, k) {
            s[k] = v;
        }, this));

        this.dataset.save(s, { success: function() {
            $("#edit-dataset-alert").alert("success", "Saved!");
        }});

        return false;
    },

    destroy: function() {
        this.dataset.destroy({ success: _.bind(function() {
            this.dataset = null;
            $("#dataset-destroy-modal").modal("hide");
            window.location = '#datasets';
        }, this)});
    },

    download: function() {
        this.dataset.data_upload.download(); 
    }
});

