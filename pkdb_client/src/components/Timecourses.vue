<template>
    <GetData :resource_url="resource_url" >
        <div slot-scope="resource">
            <TimecoursesTable :resource="resource" :api="api" :resource_url="resource_url" />
        </div>
    </GetData>
</template>
<script>
    import TimecourseSmall from './TimecourseSmall';
    import GetData from './GetPaginatedData';
    import TimecoursesTable from "./TimecoursesTable";

export default {
    name: 'Timecourses',
    components: {
        GetData:GetData,
        TimecoursesTable:TimecoursesTable,
        TimecourseSmall: TimecourseSmall,
    },
    props: {
        api: String
    },

    data() {
        return {
            resource_url: this.api + '/timecourses_read/?format=json&final=True',
            }
        }
}
</script>
<style>
</style>