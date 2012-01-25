PANDA.views.DatasetResults = Backbone.View.extend({
    dataset: null,

    initialize: function(options) {
        _.bindAll(this, "render");

        this.search = options.search;
    },

    set_dataset: function(dataset) {
        this.dataset = dataset;
        this.dataset.data.bind("reset", this.render);
    },

    render: function() {
        var context = this.dataset.data.meta;
        context["settings"] = PANDA.settings;

        context["query"] = this.search.query,
        context["root_url"] = "#dataset/" + this.dataset.get("slug") + "/search/" + this.search.query;

        context["pager_unit"] = "row";
        context["row_count"] = this.dataset.get("row_count");

        context["pager"] = PANDA.templates.pager(context);
        context["dataset"] = this.dataset.results();

        this.el.html(PANDA.templates.dataset_results(context));
    }
});
