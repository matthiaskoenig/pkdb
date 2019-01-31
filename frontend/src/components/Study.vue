<template>
    <span id="study">
        <get-data :resource_url="resource_url">
            <div slot-scope="study">
                <get-data :resource_url="study_pks_url">
                    <div slot-scope="study_pks">
                        <StudyDetail :study="study.data" :study_pks="study_pks.data" :resource_url="resource_url" />
                    </div>
                </get-data>
            </div>

        </get-data>
    </span>
</template>

<script>
    import StudyDetail from './detail/StudyDetail'

    export default {
        name: 'Study',
        components: {
            StudyDetail
        },

        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/studies_elastic/'+ entry_id +'/?format=json';
            },
            study_pks_url(){
                return this.$store.state.endpoints.api + '/study_pks/?format=json'
            }
        },
    }
</script>
<style>
</style>