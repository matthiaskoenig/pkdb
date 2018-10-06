<template>
    <div id="group-detail">
        <GetData :resource_url="resource_url">
            <div slot-scope="group">
                <GroupDetail :group="group.data" :resource_url="resource_url" />
            </div>
        </GetData>
    </div>
</template>

<script>
    import GroupDetail from '@/components/detail/GroupDetail'

    export default {
        name: 'Group',
        components: {
            GroupDetail: GroupDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var group_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/groups_read/'+ group_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>