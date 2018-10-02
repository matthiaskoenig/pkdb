<template>

    <GetPaginatedData :resource_url="resource_url">
        <div slot-scope="data">
            <GroupsTable :data="data" :resource_url="resource_url" />
        </div>
    </GetPaginatedData>


</template>
<script>

    import GetPaginatedData from '@/components/api/GetPaginatedData';
    import GroupsTable from "@/components/tables/GroupsTable";

    export default {
        name: 'Groups',
        components: {
            GetPaginatedData: GetPaginatedData,
            GroupsTable: GroupsTable,

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
                return this.api + '/groups_read/?format=json';
            },
        }
    }
</script>
<style>
</style>