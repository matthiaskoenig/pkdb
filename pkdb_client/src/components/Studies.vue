<template>
    <GetPaginatedData :resource_url="resource_url">
        <div slot-scope="data">
            <StudiesTable :data="data" :resource_url="resource_url" />
        </div>
    </GetPaginatedData>
</template>

<script>
    import GetPaginatedData from '@/components/api/GetPaginatedData';
    import StudiesTable from "@/components/tables/StudiesTable";

    export default {
        name: 'References',
        components: {
            GetPaginatedData: GetPaginatedData,
            StudiesTable: StudiesTable,

        },
        methods: {},
        data() {
            return {
            }
        },
        computed: { // vuex store
            api() {
                return this.$store.state.endpoints.api;
            },
            resource_url() {
                return this.api + '/studies_read/?format=json';
            },
        }
    }
</script>

<style></style>