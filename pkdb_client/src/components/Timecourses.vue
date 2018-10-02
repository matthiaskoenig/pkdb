<template>
    <GetPaginatedData :resource_url="resource_url">
        <div slot-scope="data">
            <TimecoursesTable :data="data"  :resource_url="resource_url"/>
        </div>
    </GetPaginatedData>
</template>

<script>
    import GetPaginatedData from '@/components/api/GetPaginatedData';
    import TimecoursesTable from "@/components/tables/TimecoursesTable";

    export default {
        name: 'Timecourses',
        components: {
            GetPaginatedData: GetPaginatedData,
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