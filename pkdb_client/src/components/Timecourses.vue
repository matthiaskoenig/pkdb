<template>
    <get-paginated-data :resource_url="resource_url">
        <div slot-scope="data">
            <timecourses-table :data="data" :resource_url="resource_url"/>
        </div>
    </get-paginated-data>
</template>

<script>
    import GetPaginatedData from './api/GetPaginatedData';
    import TimecoursesTable from "./tables/TimecoursesTable";

    export default {
        name: 'Timecourses',
        components: {
            GetPaginatedData: GetPaginatedData,
            TimecoursesTable: TimecoursesTable,
        },
        computed: {
            api() {
                return this.$store.state.endpoints.api
            },
            resource_url() {
                return this.api + '/timecourses_read/?format=json&final=True';
            },
        }
    }
</script>

<style>
</style>