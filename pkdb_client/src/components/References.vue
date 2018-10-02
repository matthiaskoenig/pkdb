<template>
    <GetPaginatedData :resource_url="resource_url">
        <div slot-scope="data">
            <ReferencesTable :data="data" :resource_url="resource_url" />
        </div>
    </GetPaginatedData>
</template>

<script>
    import GetPaginatedData from '@/components/api/GetPaginatedData';
    import ReferencesTable from "@/components/tables/ReferencesTable";

    export default {
        name: 'References',
        components: {
            GetPaginatedData: GetPaginatedData,
            ReferencesTable: ReferencesTable,

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
                return this.api + '/references_read/?format=json';
            },
        }
    }
</script>

<style></style>