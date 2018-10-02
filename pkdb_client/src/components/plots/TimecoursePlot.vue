<template>
    <div class="small-timeseries">
        <vue-plotly :data="data" :layout="layout" :options="options"/>
    </div>
</template>

<script>
    import {clean} from "@/utils"
    import VuePlotly from '@statnett/vue-plotly'

    export default {
        name: "TimecoursePlot",

        props: {
            timecourse: Object,

        },
        components: {
            VuePlotly,
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
                var x = this.timecourse.time;
                var type = 'scatter';
                var error_y = {
                    type: 'data',
                        array: this.timecourse.sd,
                };
                return [{x,y:this.values.y,type,error_y}];

            },
            layout(){
                var   margin = {
                    l: 5,
                    r: 5,
                    b: 5,
                    t: 5,
                    pad: 4
                };

                var yaxis = {title: this.timecourse.pktype+" "+ this.values.title_y +" "+ this.timecourse.calculate_auc_end.substance + " [" + this.timecourse.unit+ "]"};
                var xaxis = {title: "time [" + this.timecourse.time_unit+ "]"};

                return {xaxis,yaxis,autosize: false,width: 400,height: 200, margin:margin};
            },
            options(){
                return {};
            },
        }

    }
</script>

<style scoped>
</style>