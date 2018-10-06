<template>
    <div id="group-detail">
        <get-data :resource_url="resource_url">
            <div slot-scope="group">
                <group-detail :group="group.data" :resource_url="resource_url" />
            </div>
        </get-data>
    </div>
</template>

<script>
    import GroupDetail from './detail/GroupDetail'

    export default {
        name: 'Group',
        components: {
            GroupDetail: GroupDetail
        },
        computed: {

            api() {
                return this.$store.state.endpoints.api;
            },
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var group_id = tokens[tokens.length-1];
                return this.api + '/groups_read/'+ group_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>