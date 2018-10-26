<template>
    <span id="intervention">
        <get-data :resource_url="resource_url">
            <div slot-scope="intervention">
                <intervention-detail :intervention="intervention.data" :resource_url="resource_url" />
            </div>
        </get-data>
    </span>
</template>

<script>
    import InterventionDetail from './detail/InterventionDetail'

    export default {
        name: 'Intervention',
        components: {
            InterventionDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/interventions_elastic/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>