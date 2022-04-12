<template>
    <v-sheet flat>
        <table-toolbar otype="scatters" :count="count" :autofocus="autofocus" :url="url" @update="searchUpdate"/>
        <v-data-table
            fill-height
                fixed-header
                :height="windowHeight"
                :headers="headers"
                :items="entries"
                :options.sync="options"
                :server-items-length="count"
                :loading="loading"
                :class="table_class"
                :footer-props="footer_options"
        >
            <template v-slot:item.buttons="{ item }">
                <link-button v-if="item.study"
                            :sid="item.study.sid"
                            show_type_input="study"
                            :title="'Study: '+item.study.name"
                            icon="study"
                />
              <JsonButton :resource_url="api + 'subsets/'+ item.pk +'/?format=json'"/>

            </template>

          <template v-slot:item.name="{ item }">
            {{item.name}}

          </template>

            <template v-slot:item.details_x="{ item }">
              <scatter-details :details="scatter_x(item.array)"/>
            </template>
          <template v-slot:item.details_y="{ item }">
            <scatter-details :details="scatter_y(item.array)"/>
          </template>

            <template v-slot:item.scatter="{ item }">
              <scatter-plot :scatter_x="scatter_x(item.array)" :scatter_y="scatter_y(item.array)"/>
            </template>
            <no-data/>

        </v-data-table>
    </v-sheet>
</template>

<script>
    import {searchTableMixin, UrlMixin} from "./mixins";
    import TableToolbar from './TableToolbar';
    import NoData from './NoData';
    import ScatterDetails from "../detail/ScatterDetails";
    import ScatterPlot from "../plots/ScatterPlot";

    export default {
        name: "ScatterTable",
        components: {
          ScatterPlot,
            NoData,
            TableToolbar,
            ScatterDetails
        },
        methods: {
          scatter: function(array, dimension) {
            let scatter = array.map(function (point) {
              if (point.length === 2){
              return {
                "time": point[dimension].time,
                "unit": point[dimension].unit,
                "time_unit": point[dimension].time_unit,
                "sd": point[dimension].sd,
                "se": point[dimension].se,
                "cv": point[dimension].cv,
                "mean": point[dimension].mean,
                "median": point[dimension].median,
                "value": point[dimension].value,
                "individual": point[dimension].individual,
                "group": point[dimension].group,
                "interventions": point[dimension].interventions,
                "tissue": point[dimension].tissue,
                "substance": point[dimension].substance,
                "choice": point[dimension].choice,
                "measurement_type": point[dimension].measurement_type,

              }}else{
                console.log(point)
                return {}
              }
            })
            var out = {};
            for (var i = 0; i < scatter.length; i++) {
              for (var key in scatter[i]) {
                if (out[key] === undefined) {
                  out[key] = new Set();
                }
                const value = scatter[i][key]
                if (value) {
                  out[key].add(JSON.stringify(value))
                }
              }
            }
            var result = {}
            for (const [key, value] of Object.entries(out)) {
              result[key] = Array.from(value).map(JSON.parse)
            }
            return result
          },
          scatter_x: function(array){
          return this.scatter(array,0)
        },
          scatter_y: function(array){
            return this.scatter(array,1)
          },
        },
        computed:{
          },
        mixins: [searchTableMixin, UrlMixin],


        data() {
            return {
                otype: "subsets",
                otype_single: "subset",
                headers: [
                    {text: '', value: 'buttons', sortable: false},
                    {text: 'Details X', value: 'details_x',sortable: false},
                    {text: 'Details Y', value: 'details_y',sortable: false},
                    {text: 'Scatter', value: 'scatter',sortable: false},
                ]
            }
        },
    }
</script>

<style scoped>

</style>
