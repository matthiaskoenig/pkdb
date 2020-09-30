<template>
    <div id="group-detail">
        <get-data :resource_url="resource_url">
            <div slot-scope="individual">
                <div v-if="individual.loaded">
                    <individual-detail :individual="individual.data" :resource_url="resource_url" />
                </div>
            </div>
        </get-data>
    </div>
</template>

<script>
    import IndividualDetail from './IndividualDetail'

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
                return this.$store.state.endpoints.api + 'individuals/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>