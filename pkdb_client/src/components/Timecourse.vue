<template>
    <span id="timecourse">
        <get-data :resource_url="resource_url">
            <div slot-scope="timecourse">
                <timecourse-detail :timecourse="timecourse.data" :resource_url="resource_url" />
            </div>
        </get-data>
    </span>
</template>

<script>
    import TimecourseDetail from './detail/TimecourseDetail'

    export default {
        name: 'Timecourse',
        components: {
            TimecourseDetail
        },
        computed: {
            resource_url() {
                var path = this.$route.path;
                var tokens = path.split('/');
                var entry_id = tokens[tokens.length-1];
                return this.$store.state.endpoints.api + '/timecourses_elastic/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>