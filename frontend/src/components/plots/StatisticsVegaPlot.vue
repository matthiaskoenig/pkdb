<template>
    <div id="vis"></div>
</template>

<script>

    var spec = "https://raw.githubusercontent.com/vega/vega/master/docs/examples/bar-chart.vg.json";
    vegaEmbed('#vis', spec).then(function(result) {
        // Access the Vega view instance (https://vega.github.io/vega/docs/api/view/) as result.view
    }).catch(console.error);

    export default {
        name: "StatisticsVegaPlot",
        props: {
        },
        components: {
        },
        computed: {}
    }
</script>

<style scoped>
</style>