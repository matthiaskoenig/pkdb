<template>
    <div id="timecourse">
        <GetData :resource_url="resource_url">
            <div slot-scope="timecourse">
                <div v-if="timecourse.loaded">
                    <TimecourseDetail :timecourse="timecourse.data" :resource_url="resource_url" />
                </div>
            </div>
        </GetData>
    </div>
</template>

<script>
    import TimecourseDetail from '@/components/detail/TimecourseDetail'

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
                return this.$store.state.endpoints.api + '/timecourses_read/'+ entry_id +'/?format=json';
            }
        },
    }
</script>
<style>
</style>