<template>
    <div id="group-detail">
        <GetData :resource_url="resource_url">
            <div slot-scope="individual">
                <div v-if="individual.loaded">
                    <IndividualDetail :individual="individual.data" :resource_url="resource_url" />
                </div>
            </div>
        </GetData>
    </div>
</template>

<script>
    import IndividualDetail from '@/components/detail/IndividualDetail'

    export default {
        name: 'Individual',
        components: {
            IndividualDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/individuals_read/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>