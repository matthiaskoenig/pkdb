<template>
    <div>
        <md-card class="md-card">
            <md-card-header>
                <md-card-header-text class="md-card-header-text" >
                    <div class="md-title">{{timecourse_no_options.choice}}</div>
                    <div class="md-subhead title_sub">{{timecourse_no_options.category}}</div>
                </md-card-header-text>
            </md-card-header>

            <md-card-content>
                <div class="card-reservation">
                    <div v-for="(value, key) in timecourse_clean">
                        <span>{{value}} </span>
                        <div class="md-subhead">{{key}}</div>

                    </div>
                </div>

            </md-card-content>

        </md-card>
        <vue-plotly :data="data" :layout="layout" :options="options"/>
        <div>
            <img :src="timecourse.figure" alt="Responsive image" />
        </div>

    </div>

</template>

<script>
    import axios from 'axios'
    import VuePlotly from '@statnett/vue-plotly'
    import {clean} from "@/utils"

    export default {
        name: "TimecourseDetail",

        props: {
            api: String,
            id: String,
            parent_count: Number,

        },
        components: {
            VuePlotly,
        },

        data() {
            return {
                timecourse: {},
                resource_url: this.api + '/timecourses_read/' + this.id + '/?format=json',

            }
        },
        // Fetches posts when the component is created.
        created() {
            axios.get(this.resource_url)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.timecourse = response.data
                })
                .catch(e => {
                    this.errors.push(e)
                })
        },
        computed: {
            timecourse_no_options(){
                delete this.timecourse.options;
                return this.timecourse;
            },
            timecourse_clean(){
                delete this.timecourse_no_options.pk;
                //delete this.timecourse_no_options.final;
                if (this.parent_count === this.timecourse_no_options.count ) {
                    delete this.timecourse_no_options.count
                }
                clean(this.timecourse_no_options);

                return this.timecourse_no_options;
            },
            values(){
                var y;
                var title_y;
                if  (this.timecourse.value != null && this.timecourse.value !== undefined) {
                    y = this.timecourse.value;
                    title_y = "value"


                }
                else if (this.timecourse.mean != null && this.timecourse.mean !== undefined){
                    y = this.timecourse.mean;
                    title_y = "mean"

                }
                else if (this.timecourse.median != null && this.timecourse.median !== undefined){
                    y = this.timecourse.median;
                    title_y = "median"

                }
                return {y,title_y};
            },
            data(){
                var y;
                var x;
                var type = 'scatter';
                var error_y;
                x = this.timecourse.time;
                error_y = {
                    type: 'data',
                        array: this.timecourse.sd,
                };
                return [{x,y:this.values.y,type,error_y}];

            },
            layout(){
                //xaxis: {title: this.timecourse.time_unit },
                var yaxis = {title: this.timecourse.pktype+" "+ this.values.title_y +" "+ this.timecourse.calculate_auc_end.substance + " [" + this.timecourse.unit+ "]"};
                var xaxis = {title: "time [" + this.timecourse.time_unit+ "]"};

                return {xaxis,yaxis};
            },
            options(){
                return {};
            },
        }

    }


</script>

<style  scoped>

    .md-card {
        width: 320px;
        margin: 4px;
        display: table-cell;
        vertical-align: top;
        align-items: stretch;
    }
    .card-reservation {
        margin-top: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;

    }
    .md-title{
        text-align: left;
    }
    .title_sub{
        text-align: left;
        align-self: flex-end;


    }

</style>