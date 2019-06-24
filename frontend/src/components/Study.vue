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
            study_id(){
                let path = this.$route.path;
                let tokens = path.split('/');
                return tokens[tokens.length-1];
            },
            resource_url() {
                return this.$store.state.endpoints.api + '/studies_elastic/'+ this.study_id +'/?format=json';
            },
            study_pks_url(){
                return this.$store.state.endpoints.api + '/study_pks/?format=json'
            }
        },
    }
</script>
<style>
</style>