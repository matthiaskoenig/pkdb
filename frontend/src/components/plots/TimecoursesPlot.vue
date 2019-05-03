<template>
    <span class="small-timeseries">
        <vue-plotly :data="timecourses_data" :layout="layout()" :options="options()"/>
    </span>
</template>

<script>
    import VuePlotly from '@statnett/vue-plotly'

    export default {
        name: "TimecoursesPlot",
        props: {
            timecourses: {
                type: Array,
                required: true
            },
        },
        components: {
            VuePlotly,
        },
        computed: {
            timecourses_data(){
                return this.timecourses.map(timecourse => this.timecourse_data(timecourse));
            },
        },
        methods: {
            values(timecourse){
                var y;
                var title_y;
                if  (timecourse.value != null && timecourse.value !== undefined) {
                    y = timecourse.value;
                    title_y = "value"
                }
                else if (timecourse.mean != null && timecourse.mean !== undefined){
                    y = timecourse.mean;
                    title_y = "mean"
                }
                else if (timecourse.median != null && timecourse.median !== undefined){
                    y = timecourse.median;
                    title_y = "median"
                }
                return {y, title_y};
            },
            errors(timecourse){
                var y;
                var title_y;
                if  (timecourse.sd != null && timecourse.sd !== undefined) {
                    y = timecourse.sd;
                    title_y = "sd"
                }
                else if (timecourse.se != null && timecourse.se !== undefined){
                    y = timecourse.se;
                    title_y = "se"
                }
                else if (timecourse.cv != null && timecourse.cv !== undefined){
                    y = timecourse.cv;
                    title_y = "cv"
                }
                return {y, title_y};
            },

            name(timecourse) {
                var name = "";
                if (timecourse.group){
                    name += timecourse.group.name ;
                }
                else if (timecourse.individual){
                    name += timecourse.individual.name;
                }
                timecourse.interventions.forEach(function(internvention){

                    console.log(internvention);
                    name += " " + internvention.name;
                });
                name += " " + timecourse.substance.name;

                return name
            },
            timecourse_data(timecourse,){
                return {
                    x: timecourse.time,
                    y: this.values(timecourse).y,
                    type: 'scatter',
                    error_y: {
                        type: 'data',
                        array: this.errors(timecourse).y,
                        visible: true,
                        //color: '#555555',
                    },
                    marker: {
                        //color: '#000000',
                        size: 5
                    },
                    name: this.name(timecourse)
                }
            },

            layout(){
                let unqiue_time_unit = [...new Set( this.timecourses.map(x => x.time_unit))];
                let time_unit = "";
                let y_font_color = "black";
                let x_font_color = "black";

                if ( unqiue_time_unit.length !== 1) {
                    time_unit = "Problem: multiple units"
                    x_font_color = "red"

                }
                else {
                    time_unit = unqiue_time_unit[0]
                }

                let unqiue_unit = [...new Set( this.timecourses.map(x => x.unit))];
                let unit = "";
                if ( unqiue_unit.length !== 1) {
                    unit = "Problem: multiple units";
                    y_font_color = "red"
                }
                else {
                    unit = unqiue_unit[0]
                }




                var xaxis = {

                    title: "time [" +time_unit+ "]",
                    titlefont: {
                        size: 10,
                        color: x_font_color
                    },
                    showticklabels: true,
                    tickfont: {
                        size: 10,
                        color: 'black'
                    },
                };
                var yaxis = {
                    title: this.timecourses[0].substance.name + " [" + unit+ "]",
                    titlefont: {
                        size: 10,
                        color: y_font_color
                    },
                    showticklabels: true,
                    tickfont: {
                        size: 10,
                        color: 'black'
                    },
                };


                return {
                    xaxis,
                    yaxis,
                    legend: {x:-.1, y:1.2},

                    autosize: true,
                    width: 700,
                    height: 400,
                    margin:{ l: 40, r: 0, b: 30, t: 5, pad: 0 }

                };
            },
            options(){
                return {
                    displayModeBar: false
                };
            },
        }

    }
</script>

<style scoped>
</style>