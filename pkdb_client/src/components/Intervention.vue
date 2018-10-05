<template>
    <div id="intervention">
        <GetData :resource_url="resource_url">
            <div slot-scope="intervention">
                <div v-if="intervention.loaded">
                    <InterventionDetail :intervention="intervention.data" :resource_url="resource_url" />
                </div>
            </div>
        </GetData>
    </div>
</template>

<script>
    import InterventionDetail from '@/components/detail/InterventionDetail'

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
                return this.$store.state.endpoints.api + '/interventions_read/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>