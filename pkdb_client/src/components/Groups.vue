<template>
    <GetData :resource_url="resource_url">
        <div slot-scope="resource">
            <GroupsTable :resource="resource" :resource_url="resource_url" />
        </div>
    </GetData>

</template>
<script>

    import GetData from '@/components/api/GetPaginatedData';
    import GroupsTable from "@/components/tables/GroupsTable";

    export default {
        name: 'Groups',
        components: {
            GetData: GetData,
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