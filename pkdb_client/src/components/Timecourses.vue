<template>
    <GetData :resource_url="resource_url">
        <div slot-scope="resource">
            <TimecoursesTable :resource="resource"  :resource_url="resource_url"/>
        </div>
    </GetData>
</template>

<script>
    import GetData from '@/components/api/GetPaginatedData';
    import TimecoursesTable from "@/components/tables/TimecoursesTable";

    export default {
        name: 'Timecourses',
        components: {
            GetData: GetData,
            TimecoursesTable: TimecoursesTable,
        },
        computed: {
            api() {return this.$store.state.endpoints.api},
            resource_url() {
                return this.api + '/timecourses_read/?format=json&final=True';
            },
        }
    }
</script>
<style>
</style>